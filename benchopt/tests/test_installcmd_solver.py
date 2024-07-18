import pytest

from benchopt.cli.main import install
from benchopt.utils.temp_benchmark import temp_benchmark


def test_invalid_install_cmd():
    # Solver with an invalid install command
    invalid_solver = """
    from benchopt import BaseSolver, safe_import_context

    with safe_import_context() as import_ctx:
        raise ImportError()


    class Solver(BaseSolver):
        name = "invalid-solver"
        install_cmd = "invalid_command"
        requirements = []
        def set_objective(self, X, y, lmbd): pass
        def run(self, n_iter): pass
        def get_result(self): return dict(beta=1)
    """

    with temp_benchmark(solvers=[invalid_solver]) as benchmark:
        with pytest.raises(ValueError, match="is not a valid"):
            install(
                [str(benchmark.benchmark_dir), '-y', '-s', 'invalid-solver'],
                standalone_mode=False
            )


def test_conda_default_install_cmd():
    # Solver class without the install_cmd attribute
    # Checks if conda is used by default.
    solver_noinstall = """
    from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = "solver-no-install-cmd"
        requirements = []
        def set_objective(self, X, y, lmbd): pass
        def run(self, n_iter): pass
        def get_result(self): return dict(beta=1)
    """

    with temp_benchmark(solvers=[solver_noinstall]) as benchmark:
        SolverClass, _ = benchmark.check_solver_patterns(
            ["solver-no-install-cmd"]
        )[0]
        solver_instance = SolverClass()

        # Check that the default 'install_cmd' is 'conda'
        assert getattr(solver_instance, "install_cmd", "conda") == "conda"
