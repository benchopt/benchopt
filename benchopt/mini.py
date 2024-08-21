from pathlib import Path
from functools import partial


from .base import BaseSolver
from .base import BaseDataset
from .base import BaseObjective
from .benchmark import Benchmark
from .utils.dynamic_modules import get_file_hash
from .utils.safe_import import safe_import_context
from .utils.safe_import import set_benchmark_module

from .stopping_criterion import SingleRunCriterion
from .stopping_criterion import SufficientProgressCriterion

_datasets = []
_solvers = []
_objective = None


def iterable(x):
    from collections.abc import Iterable
    return isinstance(x, Iterable)


class _InstallDepsMixing:

    _import_ctx = safe_import_context()

    @classmethod
    def is_installed(cls, env_name=None, raise_on_not_installed=None,
                     quiet=False):
        return True

    @staticmethod
    def _reconstruct(mini_file, pickled_hash, parameters, hook_args,
                     klass, name):
        benchmark = get_mini_benchmark(mini_file)

        if klass == "_Objective":
            klass = benchmark.get_benchmark_objective()
        elif klass == "_Dataset":
            klass = [c for c in benchmark.get_datasets() if c.name == name][0]
        elif klass == "_Solver":
            klass = [c for c in benchmark.get_solvers() if c.name == name][0]

        obj = klass.get_instance(**parameters)
        if hook_args is not None:
            _, reconstruc_hook = obj.get_pickle_hooks()
            reconstruc_hook(obj, hook_args)
        return obj

    def __reduce__(self):
        file_hash = get_file_hash(self.mini_file)
        reduce_hook, _ = self.get_pickle_hooks()
        hook_args = reduce_hook(self)

        return self._reconstruct, (
            self.mini_file, file_hash, self._parameters, hook_args,
            self.__class__.__name__, self.name
        )


class _MiniBenchmark(Benchmark):
    def __init__(self, mini_file):

        from benchopt.utils.dynamic_modules import _get_module_from_file
        _get_module_from_file(mini_file)

        assert _objective is not None, "Need to set one objective."
        assert len(_solvers) > 0, "Need to set at least one solver."
        assert len(_datasets) > 0, "Need to set at least one dataset."

        self.mini_file = Path(mini_file)
        self.benchmark_dir = Path()
        set_benchmark_module(self.benchmark_dir)

        self.pretty_name = _objective.name
        self.url = "mini_bench"
        self.min_version = _objective.min_benchopt_version
        self.name = "mini-bench"

        # Store the mini_file argument in each component
        _objective.mini_file = mini_file
        for d in _datasets:
            d.mini_file = mini_file
        for s in _solvers:
            s.mini_file = mini_file

    def __del__(self):
        global _objective
        _objective = None
        global _solvers
        _solvers = []
        global _datasets
        _datasets = []

    def get_benchmark_objective(self):
        return _objective

    def get_datasets(self):
        return _datasets

    def get_solvers(self):
        return _solvers


def dataset(func=None, name=None, **kwargs):
    if func is None:
        return partial(dataset, name=name, **kwargs)

    name_ = name if name is not None else func.__name__

    class _Dataset(_InstallDepsMixing, BaseDataset):
        name = name_
        _klass = "dataset"
        _module_filename = func.__code__.co_filename

        parameters = {k: v if iterable(v) else [v] for k, v in kwargs.items()}

        def get_data(self):
            params = {k: getattr(self, k) for k in kwargs}
            return func(**params)

    _datasets.append(_Dataset)


def solver(func=None, name=None, run_once=False, **params):
    if func is None:
        return partial(solver, name=name, run_once=run_once, **params)

    name_ = name if name is not None else func.__name__

    class _Solver(_InstallDepsMixing, BaseSolver):
        name = name_
        _module_filename = func.__code__.co_filename

        parameters = {k: v if iterable(v) else [v] for k, v in params.items()}

        sampling_strategy = "iteration"
        stopping_criterion = (
            SingleRunCriterion() if run_once else SufficientProgressCriterion()
        )

        def set_objective(self, **kwargs):
            self.kwargs = kwargs

        def warm_up(self):
            self.run(2)

        def run(self, n_iter):
            params_ = {k: getattr(self, k) for k in params}
            if run_once:
                self.res = func(**self.kwargs, **params_)
            else:
                self.res = func(n_iter, **self.kwargs, **params_)

        def get_result(self):
            return self.res

    _solvers.append(_Solver)


def objective(func=None, name=None, min_benchopt_version=None):
    if func is None:
        return partial(objective, name=name)

    global _objective
    assert _objective is None, "Can only call objective decorator once."

    name_ = name if name is not None else func.__name__
    min_benchopt_version_ = min_benchopt_version

    class _Objective(_InstallDepsMixing, BaseObjective):
        name = name_
        min_benchopt_version = min_benchopt_version_
        _module_filename = func.__code__.co_filename

        def set_data(self, **kwargs):
            self.data_kwargs = kwargs

        def get_objective(self):
            return self.data_kwargs

        def evaluate_result(self, **result):
            return func(**result)

        def get_one_result(self):
            raise RuntimeError("Should never be called.")

    _objective = _Objective


def get_mini_benchmark(mini_file):
    return _MiniBenchmark(mini_file)
