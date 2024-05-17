import pytest

from benchopt.cli.main import run
from benchopt.tests import SELECT_ONE_SIMULATED
from benchopt.utils.temp_benchmark import temp_benchmark

import tempfile
import importlib.util
from pathlib import Path


def test_invalid_install_cmd():
    # Solver with an invalid install command
    invalid_solver = """
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
        with pytest.raises(ValueError):
            run(
                [
                    str(benchmark.benchmark_dir),
                    "-s",
                    "invalid-solver",
                    "-d",
                    SELECT_ONE_SIMULATED,
                    "--no-plot",
                ],
                standalone_mode=False,
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

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        solver_path = tmpdir_path / "solver_no_install_cmd.py"

        # Write the solver code to a temporary file
        with open(solver_path, "w") as f:
            f.write(solver_noinstall)

        # Load the solver module from the temporary file
        spec = importlib.util.spec_from_file_location(
            "solver_no_install_cmd", solver_path
        )
        solver_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(solver_module)

        # Get the Solver class from the module
        SolverClass = solver_module.Solver

        # Instantiate the solver
        solver_instance = SolverClass()

        # Check that the default 'install_cmd' is 'conda'
        assert getattr(solver_instance, "install_cmd", "conda") == "conda"
