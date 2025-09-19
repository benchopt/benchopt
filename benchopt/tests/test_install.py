import re
import pytest

from benchopt.cli.main import install
from benchopt.tests.utils import CaptureCmdOutput
from benchopt.utils.temp_benchmark import temp_benchmark


def test_invalid_install_cmd():
    # Solver with an invalid install command
    invalid_solver = """
    import fake_module
    from benchopt import BaseSolver

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


def test_gpu_flag(no_debug_log):

    objective = """from benchopt import BaseObjective

        class Objective(BaseObjective):
            name = "test_obj"
            min_benchopt_version = "0.0.0"

            def set_data(self, X, y): pass
            def get_one_result(self): pass
            def evaluate_result(self, beta): return dict(value=1)
            def get_objective(self): return dict(X=0, y=0)
    """

    solver1 = """from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = "solver1"
        requirements = {"wrong_key": 1, "cpu": []}
    """

    solver2 = """from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = "solver2"
        requirements = {"gpu": [], "cpu": ["unknown_implausible_pkg"]}
        sampling_strategy = 'iteration'
    """

    with temp_benchmark(objective=objective,
                        solvers=[solver1, solver2],
                        ) as benchmark:
        err = ("keys should be `cpu` and `gpu`, got ['wrong_key', 'cpu']")
        with CaptureCmdOutput():
            with pytest.raises(ValueError, match=re.escape(err)):
                install([str(benchmark.benchmark_dir),
                         *'-y -f -s solver1 --gpu'.split()],
                        standalone_mode=False)

        # installing without gpu flag installs requirements["cpu"], hence OK
        with CaptureCmdOutput() as out:
            install([str(benchmark.benchmark_dir),
                     *'-y -f -s solver1'.split()],
                    standalone_mode=False)
        out.check_output("All required solvers are already installed.")

        # all good with requirements["gpu"] for solver2, hence no error
        with CaptureCmdOutput() as out:
            install([str(benchmark.benchmark_dir),
                     *'-y -f -s solver2 --gpu'.split()],
                    standalone_mode=False)
        out.check_output("All required solvers are already installed.")
