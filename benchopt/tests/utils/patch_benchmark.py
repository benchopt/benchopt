import sys
import builtins
from contextlib import contextmanager


class FakeModule:
    __version__ = "1.0"


@contextmanager
def patch_benchmark(benchmark, component="objective", **updates):
    "Patch a component of a given benchmark in the current interpreter"

    if component == "objective":
        obj = benchmark.get_benchmark_objective()
    else:
        raise ValueError("invalid component")

    try:
        na = object()
        prev_value = {}
        for k, v in updates.items():
            prev_value[k] = getattr(obj, k, na)
            setattr(obj, k, v)
        yield
    finally:
        for k, v in prev_value.items():
            if k is na:
                delattr(obj, k)
            else:
                setattr(obj, k, v)


@contextmanager
def patch_import(**func_import):
    """Patch import in a context.

    Given module names and asssociated functions, call the function when the
    module is imported. If the function returns None, the true import is then
    called. Otherwise, returns the function returns as the module.
    """

    builtins_import = builtins.__import__

    # Make sure we reimport the benchmark component after patching the imports
    for k in list(sys.modules):
        if 'benchopt_benchmarks' in k:
            del sys.modules[k]

    def fake_import(name, *args, **kwargs):
        if name in func_import:
            mod = func_import[name]()
            if mod is not None:
                return mod

        return builtins_import(name, *args, **kwargs)

    try:
        builtins.__import__ = fake_import
        yield
    finally:
        builtins.__import__ = builtins_import
