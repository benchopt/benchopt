import os
import time
import tempfile
import numpy as np
import pandas as pd
from joblib import Memory
from abc import ABC, abstractmethod
import matplotlib.pyplot as plt
from collections import namedtuple
from importlib import import_module

from .util import get_solvers


SAMPLING_STRATEGIES = ['n_iter', 'tolerance']

Cost = namedtuple('Cost', 'data method n_iter time loss'.split(' '))


CACHE_DIR = '.'
mem = Memory(location=CACHE_DIR, verbose=0)


class BaseSolver(ABC):

    # TODO: sampling strategy with eps/tol instead for solvers that do not
    #       expose the max number of iterations
    sampling_strategy = 'n_iter'

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

    def set_loss(self, loss_parameters):
        """Prepare the data"""
        self.dump_loss(loss_parameters)

    def run(self, n_iter):
        cmd_line = self.get_command_line(n_iter)
        os.system(cmd_line)


@mem.cache
def run_one_method(data_name, method_class, score, loss_parameters, parameters,
                   max_iter):
    method = method_class(*parameters)
    method.set_loss(loss_parameters)
    res = []
    list_iter = np.unique(np.logspace(0, np.log10(max_iter), 20, dtype=int))
    for n_iter in list_iter:
        print(f"{method.name}: {n_iter} / {max_iter}\r", end='', flush=True)
        t_start = time.time()
        method.run(n_iter=n_iter)
        delta_t = time.time() - t_start
        beta_hat_i = method.get_result()
        loss_value = score(*loss_parameters, beta_hat_i)
        res.append(Cost(data=data_name, method=method.name, n_iter=n_iter,
                        time=delta_t, loss=loss_value))
    print(f"{method.name}: done".ljust(40))
    return res


def run_benchmark(benchmark, max_iter=10):

    module_name = f"benchmarks.{benchmark}"
    module = import_module(module_name)
    score = module.score_result
    datasets = module.DATASETS

    solvers, *_ = get_solvers(benchmark)
    solver_classes = [import_module(f"{module_name}.{solver_cmd}").Solver
                      for solver_cmd in solvers]

    res = []
    for data_name, (get_data, args) in datasets.items():
        loss = get_data(**args)
        for solver in solver_classes:
            parameters = {}
            # if solver.name in ['Blitz']:
            #     run_one_method.call(data_name, solver, score, loss,
            #                         parameters, max_iter)
            try:
                res.extend(run_one_method(data_name, solver, score, loss,
                                          parameters, max_iter))
            except Exception:
                import traceback
                traceback.print_exc()
    df = pd.DataFrame(res)
    plot_benchmark(df)


def plot_benchmark(df):
    datasets = df.data.unique()
    methods = df.method.unique()
    for data in datasets:
        plt.figure(data)
        df_data = df[df.data == data]
        c_star = df_data.loss.min()
        for m in methods:
            df_ = df_data[df_data.method == m]
            plt.loglog(df_.time, df_.loss - c_star + 1e-7, label=m)
        plt.legend()
    plt.show()
