"""Decorator-based API for single-file benchmarks.

This module provides a lightweight alternative to the directory-based
benchmark structure.  An entire benchmark can be written in a single Python
file using the three decorators :func:`dataset`, :func:`solver`, and
:func:`objective`, and then run with :func:`get_benchmark`.

Example
-------
>>> from benchopt.mini import solver, dataset, objective, get_benchmark
>>>
>>> @dataset(size=100, random_state=0)
... def simulated(size, random_state):
...     X = list(range(size))
...     return dict(X=X)
>>>
>>> @solver(name="Solver 1", lr=[1e-2, 1e-3])
... def solver1(n_iter, X, lr):
...     return dict(beta=sum(X) * lr)
>>>
>>> @objective(name="My Benchmark")
... def evaluate(beta):
...     return dict(value=beta)
>>>
>>> bench = get_benchmark()
"""

import sys
import inspect
import tempfile
from pathlib import Path

import benchopt.benchmark as _bm_module
from .base import BaseSolver, BaseDataset, BaseObjective
from .benchmark import Benchmark
from .utils.dynamic_modules import get_file_hash

# ---------------------------------------------------------------------------
# Per-module registries (keyed by the resolved source file path so that
# multiple mini-bench files in the same process stay independent).
# ---------------------------------------------------------------------------
_MINI_DATASETS: list = []
_MINI_SOLVERS: list = []
_MINI_OBJECTIVES: list = []


def _set_class_module_info(klass, fn):
    """Attach _module_filename / _file_hash to a dynamically generated class.

    These attributes are expected by DependenciesMixin (is_installed) and
    by ParametrizedNameMixin (_get_mixin_args for pickling).

    The class is also registered under ``benchopt.mini.<klass.__name__>`` so
    that joblib's pickle-based hasher can find it by its qualified name.
    """
    try:
        src_file = Path(inspect.getfile(fn)).resolve()
    except (TypeError, OSError):
        src_file = Path(__file__).resolve()
    klass._module_filename = src_file
    klass._file_hash = get_file_hash(src_file)
    # _benchmark_dir is only needed for conda-env checks (not used in-process)
    klass._benchmark_dir = src_file.parent

    # Make the class importable as benchopt.mini.<name> so that pickle /
    # joblib hashing can find it via its __module__.__qualname__ path.
    klass.__module__ = "benchopt.mini"
    sys.modules["benchopt.mini"].__dict__[klass.__name__] = klass


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------

def dataset(**params):
    """Register a function as a mini-benchmark dataset.

    Parameters
    ----------
    **params : dict
        Parameter grid for the dataset.  Each value may be a list (sweep)
        or a scalar (fixed).  Matches the ``parameters`` convention of
        :class:`~benchopt.BaseDataset`.

    Returns
    -------
    decorator : callable
        The class that was generated (a :class:`~benchopt.BaseDataset`
        subclass replaces the decorated function).
    """
    def decorator(fn):
        fn_name = fn.__name__
        _params = {
            k: (v if isinstance(v, (list, tuple)) else [v])
            for k, v in params.items()
        }

        class Dataset(BaseDataset):
            name = fn_name
            parameters = _params

            def get_data(self):
                return fn(**self._parameters)

        Dataset.__name__ = f"Dataset_{fn_name}"
        Dataset.__qualname__ = Dataset.__name__
        _set_class_module_info(Dataset, fn)
        _MINI_DATASETS.append(Dataset)
        return Dataset
    return decorator


def solver(name, **params):
    """Register a function as a mini-benchmark solver.

    The decorated function is called inside ``run(n_iter)`` with:

    * ``n_iter`` bound to the stop-value,
    * solver parameters (the decorator kwargs) taken from ``self.<param>``,
    * remaining arguments taken from the objective dict (i.e. the dataset
      data as forwarded by the objective's ``get_objective``).

    The function must return a ``dict`` that will be the solver result.

    Parameters
    ----------
    name : str
        Human-readable name of the solver.
    **params : dict
        Parameter grid for the solver.

    Returns
    -------
    decorator : callable
    """
    def decorator(fn):
        sig = inspect.signature(fn)
        fn_param_names = list(sig.parameters.keys())
        solver_param_names = set(params.keys())
        _params = {
            k: (v if isinstance(v, (list, tuple)) else [v])
            for k, v in params.items()
        }
        _name = name

        class Solver(BaseSolver):
            name = _name
            parameters = _params
            sampling_strategy = "run_once"

            def set_objective(self, **objective_dict):
                self._objective_dict = objective_dict

            def run(self, n_iter):
                call_kwargs = {}
                for p in fn_param_names:
                    if p == "n_iter":
                        call_kwargs["n_iter"] = n_iter
                    elif p in solver_param_names:
                        call_kwargs[p] = self._parameters[p]
                    else:
                        call_kwargs[p] = self._objective_dict[p]
                self._result = fn(**call_kwargs)

            def get_result(self):
                return self._result

        Solver.__name__ = f"Solver_{name}"
        Solver.__qualname__ = Solver.__name__
        _set_class_module_info(Solver, fn)
        _MINI_SOLVERS.append(Solver)
        return Solver
    return decorator


def objective(name):
    """Register a function as the mini-benchmark objective.

    The decorated function acts as ``evaluate_result``.  Its keyword
    arguments determine what the solver's ``get_result`` dict must contain.

    Parameters
    ----------
    name : str
        Human-readable name of the benchmark.

    Returns
    -------
    decorator : callable
    """
    def decorator(fn):
        sig = inspect.signature(fn)
        result_param_names = list(sig.parameters.keys())
        _name = name

        class Objective(BaseObjective):
            name = _name
            parameters = {}

            def set_data(self, **data):
                self._data = data

            def get_objective(self):
                return dict(self._data)

            def evaluate_result(self, **result):
                return fn(**result)

            def get_one_result(self):
                return {k: None for k in result_param_names}

        Objective.__name__ = f"Objective_{_name}"
        Objective.__qualname__ = Objective.__name__
        _set_class_module_info(Objective, fn)
        _MINI_OBJECTIVES.append(Objective)
        return Objective
    return decorator


# ---------------------------------------------------------------------------
# MiniBenchmark
# ---------------------------------------------------------------------------

class MiniBenchmark(Benchmark):
    """A :class:`~benchopt.Benchmark` built from decorator-registered classes.

    Parameters
    ----------
    objective_cls : class
        The objective class (generated by :func:`objective`).
    solver_classes : list of class
        Solver classes (generated by :func:`solver`).
    dataset_classes : list of class
        Dataset classes (generated by :func:`dataset`).
    seed : int | None
        Random seed for the benchmark.
    no_cache : bool
        If True, disable caching.
    """

    def __init__(
        self,
        objective_cls,
        solver_classes,
        dataset_classes,
        seed=None,
        no_cache=False,
    ):
        # Bypass Benchmark.__init__ entirely — no directory scanning needed.
        self._objective_cls = objective_cls
        self._solver_classes = list(solver_classes)
        self._dataset_classes = list(dataset_classes)

        # Use a temporary directory for output and cache.
        self._tmpdir = tempfile.mkdtemp(prefix="benchopt_mini_")
        self.benchmark_dir = Path(self._tmpdir)
        self.no_cache = no_cache
        self._seed = seed

        # Register as the running benchmark (required by ParametrizedNameMixin
        # and other internals that call get_running_benchmark()).
        _bm_module._RUNNING_BENCHMARK = self

        self.pretty_name = objective_cls.name
        self.url = None
        self.name = f"mini_{objective_cls.name}".replace(" ", "_")
        self.min_version = None

    # ------------------------------------------------------------------
    # Override Benchmark methods that scan the filesystem
    # ------------------------------------------------------------------

    def get_benchmark_objective(self):
        return self._objective_cls

    def check_objective_filters(self, objective_filters):
        return [(self._objective_cls, self._objective_cls.parameters)]

    def get_solvers(self):
        return self._solver_classes

    def check_solver_patterns(self, solver_patterns, class_only=False):
        pairs = [(cls, cls.parameters) for cls in self._solver_classes]
        if class_only:
            return {cls for cls, _ in pairs}
        return pairs

    def get_datasets(self):
        return self._dataset_classes

    def check_dataset_patterns(self, dataset_patterns, class_only=False):
        pairs = [(cls, cls.parameters) for cls in self._dataset_classes]
        if class_only:
            return {cls for cls, _ in pairs}
        return pairs

    # ------------------------------------------------------------------
    # Seed handling (same logic as Benchmark but without noisy print)
    # ------------------------------------------------------------------

    @property
    def seed(self):
        if self._seed is None:
            self._seed = 0
        return self._seed

    # No-op: no benchmark_utils package in a single-file benchmark.
    def set_benchmark_module(self):
        pass


# ---------------------------------------------------------------------------
# get_benchmark
# ---------------------------------------------------------------------------

def get_benchmark(seed=None, no_cache=False):
    """Collect all decorated classes from the calling module and build a
    :class:`MiniBenchmark`.

    This function inspects the caller's global namespace to identify which
    decorated classes belong to it (matched by source file path).

    Parameters
    ----------
    seed : int | None
        Random seed forwarded to :class:`MiniBenchmark`.
    no_cache : bool
        Disable caching.

    Returns
    -------
    bench : MiniBenchmark
    """
    frame = sys._getframe(1)
    calling_file_str = frame.f_globals.get("__file__", "")
    if calling_file_str:
        calling_file = Path(calling_file_str).resolve()
    else:
        calling_file = None

    def _from_calling_module(registry):
        if calling_file is None:
            return list(registry)
        return [
            cls for cls in registry
            if cls._module_filename == calling_file
        ]

    objectives = _from_calling_module(_MINI_OBJECTIVES)
    solvers = _from_calling_module(_MINI_SOLVERS)
    datasets = _from_calling_module(_MINI_DATASETS)

    if len(objectives) != 1:
        raise ValueError(
            "Expected exactly one @objective decorator, "
            f"found {len(objectives)}.:\n"
            + "\n".join(f"  - {cls.__name__} (from {cls._module_filename})"
                        for cls in objectives)
        )

    return MiniBenchmark(
        objective_cls=objectives[0],
        solver_classes=solvers,
        dataset_classes=datasets,
        seed=seed,
        no_cache=no_cache,
    )
