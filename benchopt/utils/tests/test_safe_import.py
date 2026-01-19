import pytest

from benchopt.utils.dynamic_modules import _load_class_from_module
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.tests.utils import CaptureCmdOutput


def test_import_ctx():
    solver = """
    from benchopt import BaseSolver, safe_import_context
    with safe_import_context() as import_ctx:
        import invalid_module

    class Solver(BaseSolver):
        name = "test_import_ctx"
        requirements = ['invalid_module']
        def set_objective(self, X, y, lmbd): pass
        def run(self, n_iter): pass
        def get_result(self): return dict(beta=1)
    """
    with temp_benchmark(solvers=solver) as bench:
        with CaptureCmdOutput() as out:
            solver = _load_class_from_module(
                bench.benchmark_dir,
                bench.benchmark_dir / "solvers" / "solver_0.py",
                "Solver",
            )
            assert not solver.is_installed()
            assert solver.requirements == ['invalid_module']
            assert solver.name == "test_import_ctx"

        out.check_output(
            "ModuleNotFoundError: No module named 'invalid_module'",
            repetition=1
        )


def test_import_ctx_name():
    solver = """
    from benchopt import BaseSolver, safe_import_context
    with safe_import_context() as import_ctx_wrong_name:
        import numpy as np


    class Solver(BaseSolver):
        name = "test_import_ctx"

    """
    with temp_benchmark(solvers=solver) as bench:

        err_msg = ("Import contexts should preferably be named import_ctx, "
                   "got import_ctx_wrong_name.")
        with pytest.warns(UserWarning, match=err_msg):
            _load_class_from_module(
                bench.benchmark_dir,
                bench.benchmark_dir / "solvers" / "solver_0.py",
                "Solver",
            )
