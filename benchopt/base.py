import tempfile
from abc import ABC, abstractmethod

from .utils.dynamic_modules import get_file_hash
from .utils.dynamic_modules import _reconstruct_class

from .utils.dependencies_mixing import DependenciesMixin
from .utils.parametrized_name_mixing import ParametrizedNameMixin


# Possible stop strategies
STOP_STRATEGIES = ['iteration', 'tolerance']


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

    @classmethod
    def supports_dataset(cls, dataset):
        # Check that the solver is compatible with the given dataset
        if (getattr(dataset, 'is_sparse', False)
                and not getattr(cls, 'support_sparse', True)):
            return False

        return True

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


class BaseDataset(ParametrizedNameMixin, DependenciesMixin, ABC):
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
      If a dictionary is returned, it should at least contain a key
      `objective_value` associated to a scalar value which will be used to
      detect convergence. With a dictionary, multiple metric values can be
      stored at once instead of runnning each separately.
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
        """Used to call the computation of the objective.

        This allow to standardize the output to a dictionary.
        """
        objective_dict = self.compute(beta)

        if not isinstance(objective_dict, dict):
            objective_dict = {'objective_value': objective_dict}

        return objective_dict

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
