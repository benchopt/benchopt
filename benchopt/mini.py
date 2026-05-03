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

import yaml
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


def _mini_load_instance(module_name, qualname, parameters):
    """Reconstruct a mini-benchmark class instance in a worker process.

    This is the ``__reduce__`` callable for all generated classes.  It
    imports the user's module (which re-runs the decorators and registers
    the classes) then calls ``get_instance`` on the class found at
    ``module.qualname``.
    """
    import importlib
    mod = importlib.import_module(module_name)
    cls = getattr(mod, qualname)
    return cls.get_instance(**parameters)


def _set_class_module_info(klass, fn):
    """Attach _module_filename / _file_hash to a dynamically generated class.

    These attributes are expected by DependenciesMixin (is_installed) and
    by ParametrizedNameMixin (_get_mixin_args for pickling).

    The class is made picklable by routing its ``__module__`` and
    ``__qualname__`` to the calling module, where the decorator stored it
    under the original function name.  Joblib worker processes reimport that
    module and find the class via ``module.<fn_name>``.
    """
    try:
        src_file = Path(inspect.getfile(fn)).resolve()
    except (TypeError, OSError):
        src_file = Path(__file__).resolve()
    klass._module_filename = src_file
    klass._file_hash = get_file_hash(src_file)
    # _benchmark_dir is only needed for conda-env checks (not used in-process)
    klass._benchmark_dir = src_file.parent

    # Point pickle at the calling module + the name the decorator stored the
    # class under (= fn.__name__).  Worker processes import that module and
    # resolve ``module.<fn_name>`` to find the class.
    klass.__module__ = fn.__module__
    klass.__qualname__ = fn.__name__

    # Override __reduce__ so instances serialise via _mini_load_instance
    # instead of the default ParametrizedNameMixin._load_instance, which
    # requires a directory-based Benchmark to reconstruct.
    def __reduce__(self):
        return (
            _mini_load_instance,
            (type(self).__module__, type(self).__qualname__, self._parameters),
            self._get_state(),
        )
    klass.__reduce__ = __reduce__


# ---------------------------------------------------------------------------
# Metaclass that makes the generated class itself callable as the original fn
# ---------------------------------------------------------------------------

class _CallableFnMeta(type(BaseDataset)):
    """Metaclass that makes a generated class callable like the original fn.

    Calling the class without ``_instantiate=True`` forwards the call
    directly to ``_fn``, bypassing the benchopt API entirely::

        result = my_solver(X_train, X_test, y_train, C=1.0)  # calls fn
        result = my_solver(X_train=…, X_test=…, y_train=…, C=1.0)  # also ok

    Internal benchopt instantiation goes through ``get_instance``, which is
    overridden here to pass ``_instantiate=True``, routing ``__call__`` to
    normal object construction instead.
    """

    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)

        @classmethod
        def get_instance(klass, **parameters):
            try:
                obj = klass(_instantiate=True, **parameters)
                obj.save_parameters(**parameters)
            except Exception as exception:
                cls_type = klass.__bases__[0].__name__.replace("Base", "")
                cls_name = klass.name
                exception.args = (
                    f'Error when initializing {cls_type}: "{cls_name}". '
                    f'{". ".join(str(a) for a in exception.args)}',
                )
                raise
            return obj

        # Inject into the class dict so it shadows
        # ParametrizedNameMixin.get_instance
        cls.get_instance = get_instance

    def __call__(cls, *args, _instantiate=False, **kwargs):
        if _instantiate:
            return super().__call__(**kwargs)
        return cls._fn(*args, **kwargs)


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

        class Dataset(BaseDataset, metaclass=_CallableFnMeta):
            name = fn_name
            parameters = _params
            _fn = staticmethod(fn)

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

        class Solver(BaseSolver, metaclass=_CallableFnMeta):
            name = _name
            parameters = _params
            sampling_strategy = "run_once"
            _fn = staticmethod(fn)

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
        # Parameters in the evaluate signature that come from the dataset
        # (rather than from the solver) are kept in the objective and NOT
        # forwarded to the solver via get_objective().  Which keys belong to
        # the dataset is only known at runtime, so we compute the split
        # lazily inside the methods below.
        _evaluate_params = frozenset(result_param_names)
        _name = name

        class Objective(BaseObjective, metaclass=_CallableFnMeta):
            name = _name
            parameters = {}
            _fn = staticmethod(fn)

            def set_data(self, **data):
                self._data = data

            def get_objective(self):
                # Send to the solver only dataset keys that are NOT
                # consumed by evaluate_result (those stay in the objective).
                return {
                    k: v for k, v in self._data.items()
                    if k not in _evaluate_params
                }

            def evaluate_result(self, **result):
                # Merge objective-owned data (dataset keys that appear in
                # the evaluate signature) with the solver result.
                obj_data = {
                    k: v for k, v in getattr(self, "_data", {}).items()
                    if k in _evaluate_params
                }
                return fn(**obj_data, **result)

            def get_one_result(self):
                # Solver-produced keys = evaluate params NOT in the dataset.
                data_keys = frozenset(getattr(self, "_data", {}).keys())
                return {
                    k: None for k in result_param_names
                    if k not in data_keys
                }

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
        config=None,
        run_config=None,
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

        # Write an optional config.yml into the temp directory so that
        # Benchmark.get_setting() can find it.
        if config is not None:
            cfg_path = self.benchmark_dir / "config.yml"
            if isinstance(config, dict):
                cfg_path.write_text(yaml.dump(config), encoding="utf-8")
            else:
                import shutil
                shutil.copy(str(config), str(cfg_path))

        # Register as the running benchmark (required by ParametrizedNameMixin
        # and other internals that call get_running_benchmark()).
        _bm_module._RUNNING_BENCHMARK = self

        self.pretty_name = objective_cls.name
        self.url = None
        self.name = f"mini_{objective_cls.name}".replace(" ", "_")
        self.min_version = None

        # run_config stores default kwargs forwarded to run_benchmark.
        self.run_config = dict(run_config) if run_config else {}

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

def get_benchmark(seed=None, no_cache=False, config=None, run_config=None):
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
    config : dict | str | Path | None
        Optional benchmark configuration.  Either a ``dict`` that will be
        serialised as ``config.yml`` inside the temporary benchmark
        directory, or a path to an existing YAML file that will be copied
        there.  The config follows the same format as the ``config.yml``
        used by regular benchmarks (e.g. ``plot_configs`` key for named
        plot views).
    run_config : dict | None
        Default keyword arguments forwarded to
        :func:`~benchopt.runner.run_benchmark` when running this benchmark.
        Accepted keys include ``solver_names``, ``dataset_names``,
        ``max_runs``, ``n_repetitions``, ``timeout``, etc.  These are
        stored as ``bench.run_config`` and can be unpacked at call time::

            bench = get_benchmark(run_config={"solver_names": ["Logistic*"]})
            run_benchmark(bench, **bench.run_config)

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
        config=config,
        run_config=run_config,
    )
