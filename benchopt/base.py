import tempfile
import numbers
import warnings

from abc import ABC, abstractmethod

from .stopping_criterion import SufficientProgressCriterion

from .utils.safe_import import set_benchmark
from .utils.dynamic_modules import get_file_hash
from .utils.dynamic_modules import _reconstruct_class

from .utils.dependencies_mixin import DependenciesMixin
from .utils.parametrized_name_mixin import ParametrizedNameMixin


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

    Note that two ``stopping_strategy`` can be used to construct the benchmark
    curve:

    - ``'iteration'``: call the run method with max_iter number increasing
      logarithmically to get more an more precise points.
    - ``'tolerance'``: call the run method with tolerance deacreasing
      logarithmically to get more and more precise points.

    """

    _base_class_name = 'Solver'
    stopping_criterion = SufficientProgressCriterion(
        strategy='iteration'
    )

    @property
    def _solver_strategy(self):
        """ Change stop_strategy to stopping_strategy """
        if hasattr(self, 'stop_strategy'):
            warnings.warn(
                "'stop_strategy' attribute is deprecated, "
                "use 'stopping_strategy' instead",
                FutureWarning
            )
            return self.stop_strategy
        elif hasattr(self, 'stopping_strategy'):
            return self.stopping_strategy
        else:
            return self.stopping_criterion.strategy

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

        If `stopping_strategy` is set to `"callback"`, then `run` should call
        the callback at each iteration. The callback will compute the time,
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

    @staticmethod
    def _reconstruct(module_filename, parameters, objective,
                     pickled_module_hash=None, benchmark_dir=None):
        set_benchmark(benchmark_dir)
        Solver = _reconstruct_class(
            module_filename, 'Solver', benchmark_dir, pickled_module_hash,
        )
        obj = Solver.get_instance(**parameters)
        if objective is not None:
            obj._set_objective(objective)
        return obj

    def __reduce__(self):
        module_hash = get_file_hash(self._module_filename)
        objective = getattr(self, '_objective', None)
        return self._reconstruct, (
            self._module_filename, self._parameters, objective, module_hash,
            str(self._import_ctx._benchmark_dir)
        )


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
        """Return the data to feed to the objective .

        Returns
        -------
        data: dict
            Extra parameters of the objective. The objective will be
            instanciated by calling ``Objective.set_data(**data)``.
        """
        ...

    def _get_data(self):
        "Wrapper to make sure the returned results are correctly formated."

        # Automatically cache the _data to avoid reloading it.s
        if not hasattr(self, '_data') or self._data is None:
            self._data = self.get_data()

            # XXX - Remove in version 1.3
            if type(self._data) != dict:
                import warnings
                warnings.warn(
                    "`get_data` should return a dict containing the data. "
                    "The dimension should not be returned anymore and "
                    "Objective should have a method `get_one_solution` "
                    "to provide one feasible point. This will cause an "
                    "error starting from version 1.3.",
                    FutureWarning
                )
                dimension, data = self._data

                # Make sure dimension is a tuple
                if isinstance(dimension, numbers.Integral):
                    dimension = (dimension,)
                self._data = (dimension, data)

        return self._data

    # Reduce the pickling and hashing burden by only pickling class parameters.
    @staticmethod
    def _reconstruct(module_filename, pickled_module_hash, parameters,
                     benchmark_dir):
        set_benchmark(benchmark_dir)
        Dataset = _reconstruct_class(
            module_filename, 'Dataset', benchmark_dir, pickled_module_hash,
        )
        obj = Dataset.get_instance(**parameters)
        return obj

    def __reduce__(self):
        module_hash = get_file_hash(self._module_filename)
        return self._reconstruct, (
            self._module_filename, module_hash, self._parameters,
            str(self._import_ctx._benchmark_dir)
        )


class BaseObjective(ParametrizedNameMixin, DependenciesMixin):
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
      `value` associated to a scalar value which will be used to
      detect convergence. With a dictionary, multiple metric values can be
      stored at once instead of runnning each separately.
    """

    _base_class_name = 'Objective'

    @abstractmethod
    def set_data(self, **data):
        """Store the info on a dataset to be able to compute the objective.

        Parameters
        ----------
        **data: dict
            Extra parameters of the objective. This dictionary is retrieved
            by calling ``data = Dataset.get_data()``.
        """
        ...

    @abstractmethod
    def to_dict(self):
        """Return the objective parameters for the solver.

        Returns
        -------
        objective_dict: dict
            Parameters of the objective that will be given to the solver when
            calling ``Solver.set_objective(**objective_dict)``.
        """
        ...

    @abstractmethod
    def compute(self, beta):
        """Compute the value of the objective given the current estimate beta.

        Parameters
        ----------
        beta : ndarray or tuple of ndarray
            The current estimate of the parameters being optimized.

        Returns
        -------
        objective_value : float or dict {'name': float}
            The value(s) of the objective function. If a dictionary is
            returned, it should at least contain a key `value` associated to a
            scalar value which will be used to detect convergence. With a
            dictionary, multiple metric values can be stored at once instead
            of runnning each separately.
        """
        ...

    def __call__(self, beta):
        """Used to call the computation of the objective.

        This allow to standardize the output to a dictionary.
        """
        objective_dict = self.compute(beta)

        if not isinstance(objective_dict, dict):
            objective_dict = {'value': objective_dict}

        if 'name' in objective_dict:
            raise ValueError(
                "objective output cannot be called 'name'."
            )

        # To make the objective part clear in the results, we prefix all
        # keys with `objective_`.
        objective_dict = {
            f'objective_{k}': v for k, v in objective_dict.items()
        }

        return objective_dict

    # Save the dataset object used to get the objective data so we can avoid
    # hashing the data directly.
    def set_dataset(self, dataset):
        self._dataset = dataset
        data = dataset._get_data()

        # XXX - Remove in version 1.3
        if type(data) != dict:
            self._dimension, data = data

        # Check if the dataset is compatible with the objective
        skip, reason = self.skip(**data)
        if skip:
            return skip, reason

        self.set_data(**data)
        return False,  None

    def skip(self, **data):
        """Used to decide if the ``Objective`` is compatible with the data.

        Parameters
        ----------
        **data: dict
            Extra parameters of the objective. This dictionary is retrieved
            by calling ``data = Dataset.get_data()``.

        Returns
        -------
        skip : bool
            Whether this objective should be skipped or not for this data
            (accessible in the objective attributes).
        reason : str | None
            The reason why it should be skipped for display purposes.
            If skip is False, the reason should be None.
        """
        return False, None

    def get_one_solution(self):
        """Return one point in which the objective function can be evaluated.

        This method is mainly for testing purposes, to check that the return
        computation and the return type of `Objective.compute`. It should
        return an object that can be passed to compute.

        By default, if `Dataset.get_data` returns a shape, this function will
        return an array full of 0. It can be overriden to provide a different
        point. When `Dataset.get_data` returns "object", this method must be
        overwritten.
        """
        if not hasattr(self, '_dimension'):
            raise NotImplementedError(
                "If solvers return objects, `Objective.get_one_solution` "
                "should be overriden to return an object compatible with "
                "`compute`."
            )

        # XXX - make this an abstract class in version 1.3
        import warnings
        warnings.warn(
            "Objective should have a method `get_one_solution` "
            "to provide one feasible point. This will cause an "
            "error starting from version 1.3.",
            FutureWarning
        )

        import numpy as np
        return np.zeros(self._dimension)

    # Reduce the pickling and hashing burden by only pickling class parameters.
    @staticmethod
    def _reconstruct(module_filename, pickled_module_hash, parameters,
                     dataset, benchmark_dir):
        set_benchmark(benchmark_dir)
        Objective = _reconstruct_class(
            module_filename, 'Objective', benchmark_dir, pickled_module_hash,
        )
        obj = Objective.get_instance(**parameters)
        if dataset is not None:
            obj.set_dataset(dataset)
        return obj

    def __reduce__(self):
        module_hash = get_file_hash(self._module_filename)
        dataset = getattr(self, '_dataset', None)
        return self._reconstruct, (
            self._module_filename, module_hash, self._parameters, dataset,
            str(self._import_ctx._benchmark_dir)
        )
