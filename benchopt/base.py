import os
import time
import tempfile
import numpy as np
import pandas as pd
from joblib import Memory
from collections import namedtuple
from abc import ABC, abstractmethod

from .viz import plot_benchmark
from .util import filter_solvers
from .util import check_cmd_solver
from .util import pip_install_in_env
from .util import bash_install_in_env
from .util import check_import_solver
from .util import load_benchmark_losses
from .util import list_benchmark_solvers
from .config import get_global_setting

SAMPLING_STRATEGIES = ['iteration', 'tolerance']

Cost = namedtuple('Cost', 'data scale solver n_iter time loss'.split(' '))


CACHE_DIR = get_global_setting('cache_dir')
mem = Memory(location=CACHE_DIR, verbose=0)


class BaseSolver(ABC):

    # TODO: sampling strategy with eps/tol instead for solvers that do not
    #       expose the max number of iterations
    sampling_strategy = 'iteration'

    # Information on how to install the solver. The value of install_cmd should
    # be in {None, 'pip', 'bash'}. The API reads:
    #
    # - 'pip': The solver should have attributes `install_package` and
    #          `import_name`. BenchOpt will pip install `$install_package`
    #          and check it is possible to import `$import_name` in the
    #          virtualenv.
    #
    # - 'bash': The solver should have attribute `install_script` and
    #           `cmd_name`. BenchOpt will run `install_script` in a bash and
    #           provide the virtualenv's directory as an argument. It will also
    #           check that `cmd_name` is in the virtual_env PATH.
    install_cmd = None

    def __init__(self, **parameters):
        """Instantiate a solver with the given parameters."""
        ...

    @abstractmethod
    def set_loss(self, **loss_parameters):
        """Prepare the data for the solver."""
        ...

    @abstractmethod
    def run(self, n_iter):
        """Call the solver for n_iter iterations.

        This function should not return the parameters which will be
        retrieved by a subsequent call to get_result.

        Parameters
        ----------
        n_iter : int
            Number of iteration to run the solver for. It allows to sample the
            time/accuracy curve in the benchmark.
        """
        ...

    @abstractmethod
    def get_result(self):
        """Return the parameters computed by the previous run.

        The parameters should be returned as a flattened array.

        Return:
        -------
        parameters : ndarray, shape (n_parameters,)
            The computed coefficients by the solver.
        """
        ...

    @property
    @abstractmethod
    def name(self):
        """Each solver should expose its name for plotting purposes."""
        ...

    @classmethod
    def is_installed(cls, env_name=None):
        if cls.install_cmd == 'pip':
            return check_import_solver(cls.import_name, env_name=env_name)
        elif cls.install_cmd == 'sh':
            return check_cmd_solver(cls.cmd_name, env_name=env_name)
        return True

    @classmethod
    def install(cls, env_name=None):
        if not cls.is_installed(env_name=env_name):
            print(f"Installing solver {cls.name} in {env_name}:...",
                  end='', flush=True)
            if cls.install_cmd == 'pip':
                pip_install_in_env(cls.install_package, env_name=env_name)
            elif cls.install_cmd == 'bash':
                bash_install_in_env(cls.install_script, env_name=env_name)
            print(" done")

    # @property
    # @classmethod
    # def __name__(cls):
    #     return cls.name


class CommandLineSolver(BaseSolver, ABC):
    """A base class for solvers that are called through command lines

    Solvers that derive from this class should implement three methods:

    - get_command_line(self, n_iter, lmbd, data_file): a method that returns
      the command line necessary to run the solver up to n_iter with the input
      data provided in data_file.

    - dump_loss(self, X, y): dumps the parameter to compute the loss function
      in a file and returns the name of the file. This utility is necessary to
      reduce the impact of dumping the data to the disk in the benchmark.

    - get_result(self): retrieves the result from the disk. This utility is
      necessary to reduce the impact of loading the data from the disk in the
      benchmark.

    """
    def __init__(self, **parameters):
        self._data_file = tempfile.NamedTemporaryFile()
        self._model_file = tempfile.NamedTemporaryFile()
        self.data_filename = self._data_file.name
        self.model_filename = self._model_file.name

    @abstractmethod
    def get_command_line(self, n_iter):
        """Returns the command line to call the solver for n_iter on data_file

        Parameters
        ----------
        n_iter : int
            Number of iteration to run the solver for. It allows to sample the
            time/accuracy curve in the benchmark.

        Return
        ------
        cmd_line : str
            The command line to call to run the solver for n_iter
        """
        ...

    @abstractmethod
    def dump_loss(self, loss_parameters):
        """Dump the data for the loss to the disk.

        If possible, the data should be dump to the file self.data_filename so
        it will be clean up automatically by benchopt.

        Parameters
        ----------
        loss_parameters: tuple
            Parameter to construct the loss function. The specific shape and
            the order of the parameter are described in each benchmark
            definition file.
        """
        ...

    @abstractmethod
    def get_result(self):
        """Load the data from the disk and return the coefficients

        If possible, the model should be loaded from self.model_filename so
        it will be clean up automatically by benchopt.

        Return:
        -------
        parameters : ndarray, shape (n_parameters,)
            The computed coefficients by the solver.
        """
        ...

    def set_loss(self, loss_parameters):
        """Prepare the data"""
        self.dump_loss(loss_parameters)

    def run(self, n_iter):
        cmd_line = self.get_command_line(n_iter)
        os.system(cmd_line)


@mem.cache
def run_one_solver(data_name, solver_class, loss_function, loss_parameters,
                   solver_parameters, max_iter):

    rho = 1.5
    eps = 1e-10
    max_tolerance = 1e-15

    # Instantiate the solver
    solver = solver_class(*solver_parameters)

    # Set the loss for the solver
    scale, *loss_parameters = loss_parameters
    solver.set_loss(loss_parameters)

    # Sample the performances for different accuracy, either by varying the
    # tolerance or the maximal number of iterations
    curve = []
    if solver.sampling_strategy == 'iteration':
        def get_next(x): return max(x + 1, min(int(rho * x), max_iter))

        def progress(x, delta):
            return max(x / max_iter,
                       np.log(max(delta, eps)) / np.log(eps))
    elif solver.sampling_strategy == 'tolerance':
        def get_next(x): return x / rho

        def progress(x, delta):
            return max(np.log(x) / np.log(max_tolerance),
                       np.log(max(delta, eps)) / np.log(eps))

    id_sample = 0
    sample = 1
    delta_loss = 2 * eps
    prev_loss_value = np.inf

    while (id_sample < 30 or delta_loss > eps) and (
            solver.sampling_strategy != 'iteration' or sample <= max_iter):
        print(f"{solver.name}: {progress(sample, delta_loss):6.1%}\r", end='',
              flush=True)
        t_start = time.time()
        solver.run(sample)
        delta_t = time.time() - t_start
        beta_hat_i = solver.get_result()
        loss_value = loss_function(*loss_parameters, beta_hat_i)
        curve.append(Cost(data=data_name, scale=scale, solver=solver.name,
                          n_iter=sample, time=delta_t, loss=loss_value))

        delta_loss = prev_loss_value - loss_value
        prev_loss_value = loss_value
        id_sample += 1
        sample = get_next(sample)

    # for n_iter in list_iter:
    print(f"{solver.name}: done".ljust(40))
    print(delta_loss, eps, sample)
    return curve


def run_benchmark(benchmark, solver_names=None, max_iter=10):

    # Load the benchmark function and the datasets
    loss_function, datasets = load_benchmark_losses(benchmark)

    solver_classes = list_benchmark_solvers(benchmark)
    solver_classes = filter_solvers(solver_classes,
                                    solver_names=solver_names)

    res = []
    for data_name, (get_data, args) in datasets.items():
        loss_parameters = get_data(**args)
        for solver in solver_classes:
            solver_parameters = {}
            # if solver.name in ['Blitz']:
            #     run_one_solver.call(data_name, solver, loss_function, loss,
            #                         parameters, max_iter)
            try:
                res.extend(run_one_solver(
                    data_name, solver, loss_function, loss_parameters,
                    solver_parameters, max_iter))
            except Exception:
                import traceback
                traceback.print_exc()
    df = pd.DataFrame(res)
    plot_benchmark(df)
