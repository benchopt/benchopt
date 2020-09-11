import tempfile
from collections import namedtuple
from abc import ABC, abstractmethod

from .util import product_param
from .utils.class_property import classproperty
from .utils.dynamic_modules import get_file_hash
from .utils.shell_cmd import install_in_conda_env
from .utils.shell_cmd import _run_shell_in_conda_env
from .utils.dynamic_modules import _reconstruct_class
from .utils.shell_cmd import shell_install_in_conda_env

from .config import RAISE_INSTALL_ERROR


# Possible stop strategies
STOP_STRATEGIES = ['iteration', 'tolerance']

# Named-tuple for the cost function
Cost = namedtuple('Cost', 'data scale objective solver stop_val time obj '
                          'idx_rep'.split(' '))


class ParametrizedNameMixin():
    """Mixing for parametric classes representation and naming.
    """
    parameters = {}

    def __init__(self, **parameters):
        """Default init set parameters base on the cls.parameters
        """
        parameters_ = next(product_param(self.parameters))
        parameters_.update(parameters)
        for k, v in parameters_.items():
            if not hasattr(self, k):
                setattr(self, k, v)

    def save_parameters(self, **parameters):
        self.parameters = parameters
        if not hasattr(self, 'parameter_template'):
            self.parameter_template = ",".join(
                [f"{k}={v}" for k, v in parameters.items()])
        for k, v in parameters.items():
            if not hasattr(self, k):
                setattr(self, k, v)

    @classmethod
    def get_instance(cls, **parameters):
        """Helper function to instantiate an object and save its parameters.

        Saving the parameters allow for cheap hashing and to compute parametric
        names for the objects.
        """
        obj = cls(**parameters)
        obj.save_parameters(**parameters)
        return obj

    @property
    @abstractmethod
    def name(self):
        """Each object should expose its name for plotting purposes."""
        ...

    def __repr__(self):
        """Compute the parametrized name of the instance."""
        out = f"{self.name}"
        if len(self.parameters) > 0:
            out += f"[{self.parameter_template}]".format(**self.parameters)
        return out

    @classmethod
    def _get_parametrized_name(cls, **parameters):
        """Compute the parametrized name for a given set of parameters."""
        return str(cls.get_instance(**parameters))

    @classmethod
    def _reload_class(cls, pickled_module_hash=None):

        return _reconstruct_class(
            cls._module_filename, cls._base_class_name,
            pickled_module_hash=pickled_module_hash
        )


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
    def is_installed(cls, env_name=None, raise_on_not_installed=None):
        """Check if the module caught a failed import to assert install.

        Parameters
        ----------
        env_name: str or None
            Name of the conda env where the install should be checked. If
            None, check the install in the current environment.
        raise_on_not_installed: boolean or None
            If set to True, raise an error if the requirements are not
            installed. This is mainly for testing purposes.

        Returns
        -------
        is_installed: bool
            returns True if no import failure has been detected.
        """
        if env_name is None:
            if (cls._import_ctx is not None
                    and cls._import_ctx.failed_import):
                if raise_on_not_installed:
                    exc_type, value, tb = cls._import_ctx.import_error
                    raise exc_type(value).with_traceback(tb)
                return False
            else:
                return True
        else:
            return _run_shell_in_conda_env(
                f"benchopt check-install {cls._module_filename} "
                f"{cls._base_class_name}",
                env_name=env_name, raise_on_error=raise_on_not_installed
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
                    install_file = (
                        cls._module_filename.parents[1] / 'install_scripts' /
                        cls.install_script
                    )
                    shell_install_in_conda_env(install_file, env_name=env_name)

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

    - set_objective(self, **objective_parameters): prepares the solver to be
      called on a given problem. **objective_parameters are the output of the
      method :code:`to_dict` from the benchmark objective. In particular, this
      method should dumps the parameter to compute the objective function in a
      file for command line solvers to reduce the impact of dumping the data to
      the disk in the benchmark.

    - run(self, n_iter/tolerance): performs the computation for the previously
      given objective function, after a call to :code:`set_objective`. This
      method is the one timed in the benchmark and should not perform any
      operation unrelated to  the optimization procedure.

    - get_result(self): returns the parameters computed by the previous call to
      run. For command line solvers, this retrieves the result from the disk.
      This utility is necessary to reduce the impact of loading the result from
      the disk in the benchmark.

    Note that two `stop_strategy` can be used to construct the benchmark
    curve:

    - `iteration`: call the run method with max_iter number increasing
      logarithmically to get more an more precise points.
    - `tolerance`: call the run method with tolerance deacreasing
      logarithmically to get more and more precise points.

    """

    _base_class_name = 'Solver'
    stop_strategy = 'iteration'

    def _set_objective(self, objective):
        """Store the objective to make sure this solver is picklable
        """
        self._objective = objective
        self.set_objective(**objective.to_dict())

    @abstractmethod
    def set_objective(self, **objective_dict):
        """Prepare the objective for the solver."""
        ...

    @abstractmethod
    def run(self, stop_val):
        """Call the solver with the given stop_val.

        This function should not return the parameters which will be
        retrieved by a subsequent call to get_result.

        Parameters
        ----------
        stop_val : int | float
            Value for the stopping criterion of the solver for. It allows to
            sample the time/accuracy curve in the benchmark.
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

    # TODO: use this to allow parallel computation of the benchmark.
    @staticmethod
    def _reconstruct(module_filename, parameters, objective,
                     pickled_module_hash=None):

        Solver = _reconstruct_class(
            module_filename, 'Solver', pickled_module_hash
        )
        obj = Solver.get_instance(**parameters)
        obj._set_objective(objective)
        return obj

    def __reduce__(self):
        module_hash = get_file_hash(self._module_filename)
        return self._reconstruct, (self._module_filename, module_hash,
                                   self.parameters, self._objective)


class CommandLineSolver(BaseSolver, ABC):
    """A base class for solvers that are called through command lines

    The goal of this base class is to provide easy to use temporary files and
    solvers that derive from this class should dump their data in
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

    Datasets that derive from this class should implement one method:

    - `get_data()`: retrieves/simulates the data contains in this data set and
      returns the `scale` of the data as well as a dictionary containing the
      data. This dictionary is passed as arguments of the objective function
      method `set_data`.
    """

    _base_class_name = 'Dataset'

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
            instanciated by calling `Objective.set_data(**data)`.
        """
        ...

    # Reduce the pickling and hashing burden by only pickling class parameters.
    @staticmethod
    def _reconstruct(module_filename, pickled_module_hash, parameters):
        Dataset = _reconstruct_class(
            module_filename, 'Dataset', pickled_module_hash
        )
        obj = Dataset.get_instance(**parameters)
        return obj

    def __reduce__(self):
        module_hash = get_file_hash(self._module_filename)
        return self._reconstruct, (self._module_filename, module_hash,
                                   self.parameters)


class BaseObjective(ParametrizedNameMixin):
    """Base class to define an objective function

    Objectives that derive from this class should implement three methods:

    - `set_data(**data)`: stores the info from a given dataset to be able to
      compute the objective value on these data.

    - `to_dict()`: exports the data from the dataset as well as the parameters
      from the objective function as a dictionary that will be passed as
      parameters of the solver's `set_objective` method in order to specify the
      objective function of the benchmark.

    - `compute(beta)`: computes the value of the objective function for an
      given estimate beta. Beta is given as a flat 1D vector of size
      corresponding to the `scale` value returned by `Dataset.get_data`. The
      output should be a float or a dictionary of floats.
    """

    _base_class_name = 'Objective'

    @abstractmethod
    def set_data(self, **data):
        ...

    @abstractmethod
    def to_dict(self):
        ...

    @abstractmethod
    def compute(self, beta):
        ...

    def __call__(self, beta):
        return self.compute(beta)

    # Save the dataset object used to get the objective data so we can avoid
    # hashing the data directly.
    def set_dataset(self, dataset):
        self.dataset = dataset
        _, data = dataset.get_data()
        return self.set_data(**data)

    # Reduce the pickling and hashing burden by only pickling class parameters.
    @staticmethod
    def _reconstruct(module_filename, pickled_module_hash, parameters,
                     dataset):
        Objective = _reconstruct_class(
            module_filename, 'Objective', pickled_module_hash
        )
        obj = Objective.get_instance(**parameters)
        obj.set_dataset(dataset)
        return obj

    def __reduce__(self):
        module_hash = get_file_hash(self._module_filename)
        return self._reconstruct, (self._module_filename, module_hash,
                                   self.parameters, self.dataset)
