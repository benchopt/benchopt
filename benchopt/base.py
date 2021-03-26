import tempfile
import numbers
from abc import ABC, abstractmethod

from .utils.dynamic_modules import get_file_hash
from .utils.dynamic_modules import _reconstruct_class

from .utils.dependencies_mixin import DependenciesMixin
from .utils.parametrized_name_mixin import ParametrizedNameMixin


# Possible stop strategies
STOP_STRATEGIES = ['iteration', 'tolerance', 'callback']


class BaseSolver(ParametrizedNameMixin, DependenciesMixin, ABC):
    """A base class for solver wrappers in BenchOpt.

    Solvers that derive from this class should implement three methods:

    - ``set_objective(self, **objective_parameters)``: prepares the solver to
      be called on a given problem. ``**objective_parameters`` are the output
      of the method ``to_dict`` from the benchmark objective. In particular,
      this method should dumps the parameter to compute the objective function
      in a file for command line solvers to reduce the impact of dumping the
      data to the disk in the benchmark.

    - ``run(self, n_iter/tolerance)``: performs the computation for the
      previously given objective function, after a call to ``set_objective``.
      This method is the one timed in the benchmark and should not perform any
      operation unrelated to  the optimization procedure.

    - ``get_result(self)``: returns the parameters computed by the previous
      call to run. For command line solvers, this retrieves the result from the
      disk. This utility is necessary to reduce the impact of loading the
      result from the disk in the benchmark.

    Note that two ``stop_strategy`` can be used to construct the benchmark
    curve:

    - ``'iteration'``: call the run method with max_iter number increasing
      logarithmically to get more an more precise points.
    - ``'tolerance'``: call the run method with tolerance deacreasing
      logarithmically to get more and more precise points.

    """

    _base_class_name = 'Solver'
    stop_strategy = 'iteration'

    def _set_objective(self, objective):
        """Store the objective for hashing/pickling and check its compatibility

        Parameters
        ----------
        objective: benchopt.BaseObjective
            The objective function for the current optimization problem.

        Returns
        -------
        skip : bool
            Whether this solver should be skipped or not for this objective.
        reason : str | None
            The reason why it should be skipped for display purposes.
            If skip is False, the reason should be None.
        """
        self._objective = objective
        objective_dict = objective.to_dict()

        # Check if the objective is compatible with the solver
        skip, reason = self.skip(**objective_dict)
        if skip:
            return skip, reason

        self.set_objective(**objective_dict)
        return False, None

    @abstractmethod
    def set_objective(self, **objective_dict):
        """Prepare the objective for the solver.

        Parameters
        ----------
        **objective_parameters : dict
            Dictionary obtained as the output of the method ``to_dict`` from
            the benchmark ``Objective``.
        """
        ...

    @abstractmethod
    def run(self, stop_val):
        """Call the solver with the given stop_val.

        This function should not return the parameters which will be
        retrieved by a subsequent call to get_result.

        If `stop_strategy` is set to `"callback"`, then `run` should call the
        callback at each iteration. The callback will compute the time,
        the objective function and store relevant quantities for BenchOpt.
        Else, the `stop_val` parameter should be specified.

        Parameters
        ----------
        stop_val : int | float | callable
            Value for the stopping criterion of the solver for. It allows to
            sample the time/accuracy curve in the benchmark.
            If it is a callable, then it should act as a callback. This
            callback should be called once for each iteration with argument
            the current iterate `parameters`. The callback returns False when
            the computations should stop.
        """
        ...

    @abstractmethod
    def get_result(self):
        """Return the parameters computed by the previous run.

        The parameters should be returned as a flattened array.

        Returns
        -------
        parameters : ndarray, shape ``(dimension,)`` or ``*dimension``
            The computed coefficients by the solver.
        """
        ...

    def skip(self, **objective_dict):
        """Used to decide if the ``Solver`` is compatible with the objective.

        Parameters
        ----------
        **objective_parameters : dict
            Dictionary obtained as the output of the method ``to_dict`` from
            the benchmark ``Objective``.

        Returns
        -------
        skip : bool
            Whether this solver should be skipped or not for this objective.
        reason : str | None
            The reason why it should be skipped for display purposes.
            If skip is False, the reason should be None.
        """
        # Check that the solver is compatible with the given dataset
        from scipy import sparse

        if not getattr(self, 'support_sparse', True):
            if any(sparse.issparse(v) for v in objective_dict.values()):
                return True, f"{self} does not support sparse data."

        return False, None

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
                                   self._parameters, self._objective)


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

    - ``get_data()``: retrieves/simulates the data contains in this data set
      and returns the ``dimension`` of the data as well as a dictionary
      containing the data. This dictionary is passed as arguments of the
      objective function method ``set_data``.
    """

    _base_class_name = 'Dataset'

    @abstractmethod
    def get_data(self):
        """Return the problem's dimension as well as the objective parameters.

        Returns
        -------
        dimension: int or tuple
            Dimension of the optimized parameter. The solvers should return a
            parameter of shape ``(dimension,)`` or ``*dimension``.
        data: dict
            Extra parameters of the objective. The objective will be
            instanciated by calling ``Objective.set_data(**data)``.
        """
        ...

    def _get_data(self):
        "Wrapper to make sure the returned results are correctly formated."

        dimension, data = self.get_data()

        # Make sure dimension is a tuple
        if isinstance(dimension, numbers.Integral):
            dimension = (dimension,)

        return dimension, data

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
                                   self._parameters)


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
      given estimate beta. Beta is given as np.array of size corresponding to
      the `dimension` value returned by `Dataset.get_data`. The output should
      be a float or a dictionary of floats.
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
        _, data = dataset._get_data()
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
                                   self._parameters, self.dataset)
