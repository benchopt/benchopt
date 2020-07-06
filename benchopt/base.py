import tempfile
from collections import namedtuple
from abc import ABC, abstractmethod

from .util import install_in_conda_env
from .util import _run_shell_in_conda_env
from .util import shell_install_in_conda_env
from .config import RAISE_INSTALL_ERROR
from .class_property import classproperty


# Possible sampling strategies
SAMPLING_STRATEGIES = ['iteration', 'tolerance']

# Named-tuple for the cost function
Cost = namedtuple('Cost', 'data scale objective solver sample time obj '
                          'idx_rep'.split(' '))


class ParametrizedNameMixin():
    parameters = {}

    def __init__(self, **parameters):
        self.parameters = parameters
        if not hasattr(self, 'parameter_template'):
            self.parameter_template = ",".join(
                [f"{k}={v}" for k, v in parameters.items()])

    @property
    @abstractmethod
    def name(self):
        """Each object should expose its name for plotting purposes."""
        ...

    @property
    def _name(self):
        """Hook to define a different template to format the parameters"""
        return f"{self.name}({self.parameter_template})"

    def __repr__(self):
        if len(self.parameters) == 0:
            return self.name.capitalize()
        return self._name.format(**self.parameters).capitalize()


class DependenciesMixin:
    # Information on how to install the class. The value of install_cmd should
    # be in {None, 'conda', 'shell'}. The API reads:
    #
    # - 'conda': The class should have an attribute `requirements`.
    #          BenchOpt will conda install `$requirements`, except for entries
    #          starting with `pip:` which will be installed with `pip` in the
    #          conda env.
    #
    # - 'shell': The solver should have attribute `install_script`. BenchOpt
    #           will run `install_script` in a shell and provide the conda
    #           env directory as an argument. The command should then be
    #           installed in the `bin` folder of the env and can be imported
    #           with import_shell_cmd in the safe_import_context.
    install_cmd = None

    @classproperty
    def benchmark(cls):
        return cls.__module__.split('.')[1]

    @classproperty
    def name(cls):
        return cls.__module__.split('.')[-1]

    @classmethod
    def is_installed(cls, env_name=None):
        """Check if the module caught a failed import to assert install.

        Parameters
        ----------
        env_name: str or None
            Name of the conda env where the class should be installed. If
            None, tries to install it in the current environment.

        Returns
        -------
        is_installed: bool
            returns True if no import failure has been detected.
        """
        if env_name is None:
            import importlib
            module = importlib.import_module(cls.__module__)
            if hasattr(module, 'import_ctx'):
                return not module.import_ctx.failed_import
            else:
                return True
        else:
            return _run_shell_in_conda_env(
                f"benchopt check-install {cls.benchmark} {cls.name}",
                env_name=env_name
            ) == 0

    @classmethod
    def install(cls, env_name=None, force=False):
        """Install the class in the given conda env.

        Parameters
        ----------
        env_name: str or None
            Name of the conda env where the class should be installed. If
            None, tries to install it in the current environment.
        force : boolean (default: False)
            If set to True, forces reinstallation when using conda.

        Returns
        -------
        is_installed: bool
            True if the class is correctly installed in the environment.
        """
        is_installed = cls.is_installed(env_name=env_name)

        if force or not is_installed:
            print(f"Installing {cls.name} in {env_name}:...",
                  end='', flush=True)
            try:
                if cls.install_cmd == 'conda':
                    install_in_conda_env(*cls.requirements, env_name=env_name,
                                         force=force)
                elif cls.install_cmd == 'shell':
                    shell_install_in_conda_env(cls.install_script,
                                               env_name=env_name)

            except Exception as exception:
                if RAISE_INSTALL_ERROR:
                    raise exception

            is_installed = cls.is_installed(env_name=env_name)
            if is_installed:
                print(" done")
            else:
                print(" failed")

        return is_installed


class BaseSolver(ParametrizedNameMixin, DependenciesMixin, ABC):
    """A base class for solver wrappers in BenchOpt.

    Solvers that derive from this class should implement three methods:

    - set_objective(self, **objective_parameters): prepare the solver to be
      called on a given problem. **objective_parameters are the output of the
      method :code:`to_dict` from the benchmark objective. In particular, this
      method should dumps the parameter to compute the objective function in a
      file for command line solvers to reduce the impact of dumping the data
      to the disk in the benchmark.

    - run(self, n_iter/tolerance): a method that perform the computation for
      the previously given objective, after a call to :code:`set_objective`.
      This function is the part that is timed in the benchmark and should avoid
      performing any computation unrelated to the optimization procedure.

    - get_result(self): returns the parameters computed by the previous run.
      For command line solvers, this retrieves the result from the disk. This
      utility is necessary to reduce the impact of loading the result from the
      disk in the benchmark.

    """

    # TODO: sampling strategy with eps/tol instead for solvers that do not
    #       expose the max number of iterations
    sampling_strategy = 'iteration'

    def __init__(self, **parameters):
        """Instantiate a solver with the given parameters and store them.

        All parameters `PARAM` that are passed through init will be accessible
        as `self.PARAM` in the class.
        """
        parameters_ = {k: v[0] for k, v in self.parameters.items()}
        parameters_.update(**parameters)
        super().__init__(**parameters_)
        for k, v in parameters_.items():
            setattr(self, k, v)

    def _set_objective(self, **objective_parameters):
        """Store the objective_parameters to make sure this solver is picklable
        """
        self.objective_parameters = objective_parameters
        self.set_objective(**objective_parameters)

    # @staticmethod
    # def reconstruct(klass, parameters, objective_parameters):
    #     obj = klass(**parameters)
    #     obj.set_objective(**objective_parameters)
    #     return obj

    # def __reduce__(self):
    #     return self.reconstruct, (self.__class__, self.parameters,
    #                               self.objective_parameters)

    @abstractmethod
    def set_objective(self, **objective_parameters):
        """Prepare the objective for the solver."""
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

        Returns
        -------
        parameters : ndarray, shape (n_parameters,)
            The computed coefficients by the solver.
        """
        ...


class CommandLineSolver(BaseSolver, ABC):
    """A base class for solvers that are called through command lines

    Solvers that derive from this class should dump their data in
    `self.data_filename` and the result in `self.model_filename`.
    """

    def __init__(self, **parameters):
        self._data_file = tempfile.NamedTemporaryFile()
        self._model_file = tempfile.NamedTemporaryFile()
        self.data_filename = self._data_file.name
        self.model_filename = self._model_file.name
        super().__init__(**parameters)


class BaseDataset(ParametrizedNameMixin, DependenciesMixin):
    """Base class to define a dataset in a benchmark.
    """

    @abstractmethod
    def get_data(self):
        """Return the scale of the problem as well as the objective parameters.

        Returns
        -------
        scale: int
            Size of the optimized parameter. The solvers should return a
            parameter of shape (scale,).
        data: dict
            Extra parameters of the objective. The objective will be
            instanciated by calling Objective.set_data(**data)
        """
        ...


class BaseObjective(ParametrizedNameMixin):
    """Base class to define an objective
    """

    def __init__(self, **parameters):
        """Instantiate a solver with the given parameters and store them.

        All parameters `PARAM` that are passed through init will be accessible
        as `self.PARAM` in the class.
        """
        super().__init__(**parameters)
        for k, v in parameters.items():
            setattr(self, k, v)

    @abstractmethod
    def __call__(self, beta):
        ...

    @abstractmethod
    def set_data(self, **data):
        ...

    @abstractmethod
    def to_dict(self):
        ...
