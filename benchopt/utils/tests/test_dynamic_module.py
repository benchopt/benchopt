import pytest
from joblib import Parallel, delayed

from benchopt.cli.main import run as run_cmd
from benchopt.tests.utils import CaptureCmdOutput
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.utils.temp_benchmark import DEFAULT_SOLVERS
from benchopt.cli.tests.completion_cases import _test_shell_completion


def test_pickling_dynamic_module():
    # Make sure the dynamic modules can be pickled by joblib. In particular,
    # this is necessary for nested parallelism in distributed context.
    #
    # This test check that the module containing a solver can be pickled, and
    # that the dynamic benchmark_utils module can be retrieved in the process.

    solver = """
    from benchopt import BaseSolver
    from benchmark_utils.test1 import func1

    class Solver(BaseSolver):
        name = "test-solver"
        def set_objective(self, X, y, reg): self.X, self.y = X, y
        def run(self, _): func1()
        def get_result(self): return dict(beta=1)
    """

    with temp_benchmark(
            solvers=[solver],
            benchmark_utils={'test1': 'def func1(): print("FUNC1")'}
    ) as benchmark:
        # Get the solver from the list of tuples
        Solver, _ = benchmark.check_solver_patterns(["test-solver"])[0]
        assert Solver.is_installed()

        with CaptureCmdOutput() as out:
            Solver.run(None, None)
        out.check_output("FUNC1", repetition=1)

        # This will fail if the benchmark_utils module is not pickled by value
        # by cloudpickle.
        with CaptureCmdOutput():
            Parallel(n_jobs=2)(
                delayed(Solver.run)(None, None) for _ in range(2)
            )


@pytest.mark.parametrize("params", [
    # no name
    "pass",
    # failing name
    "name = test-solver",
])
def test_ast_replacement_no_name(params):
    # Test that the AST replacement works when a dynamic module is not
    # importable. In particular, this makes sure that the module filename
    # is correctly stored in the class.

    solver = f"""
    from benchopt import BaseSolver
    failure

    class Solver(BaseSolver):
        {params}
    """
    with temp_benchmark(solvers=solver) as bench:
        # Get the solver from the list of tuples
        Solver, _ = bench.check_solver_patterns(["solver_0"])[0]
        assert not Solver.is_installed()
        with pytest.raises(ValueError) as excinfo:
            Solver.is_installed(raise_on_not_installed=True)
        assert "Could not evaluate the name" in str(excinfo.value)
        assert "'failure' is not defined" in str(excinfo.value.__cause__)

    # Check that the failing solver does not prevent other solvers to be run.
    with temp_benchmark(solvers=[*DEFAULT_SOLVERS.values(), solver]) as bench:
        run_cmd(
            f"{bench.benchmark_dir} -s test-solver --no-plot".split(),
            'benchopt', standalone_mode=False
        )

        # Check that completion also works
        _test_shell_completion(
            run_cmd, f"{bench.benchmark_dir} -s".split(),
            [("", ['test-solver', 'solver_1'])]
        )


@pytest.mark.parametrize("params", [
    # undefined install_cmd
    "install_cmd = undefined",
    # undefined requirements
    "requirements = undefined",
    # failing requirements
    "requirements = ['', f'{undefined}']",
])
def test_ast_replacement(params, no_raise_install):
    # Test that the AST replacement works when a dynamic module is not
    # importable. In particular, this makes sure that the module filename
    # is correctly stored in the class.

    solver = f"""
    from benchopt import BaseSolver
    failure

    class Solver(BaseSolver):
        name = 'my-solver'
        {params}
        def set_objective(self, X, y, lmbd): pass
        def run(self, _): pass
        def get_result(self): return dict(beta=1)
    """

    component = params.split('=')[0].strip()

    with temp_benchmark(solvers=solver) as bench:
        Solver, _ = bench.check_solver_patterns(["my-solver"])[0]
        assert not Solver.is_installed(quiet=True)
        with pytest.raises(NameError, match="'failure' is not defined"):
            Solver.is_installed(raise_on_not_installed=True)

        with pytest.raises(ValueError) as excinfo:
            print(Solver.requirements, Solver.install_cmd)

        assert "Could not evaluate statically" in str(excinfo.value)
        assert "solver_0.py" in str(excinfo.value)
        assert f"'{component}'" in str(excinfo.value)

    # Check that the failing solver does not prevent other solvers to be run.
    with temp_benchmark(solvers=[*DEFAULT_SOLVERS.values(), solver]) as bench:
        run_cmd(
            f"{bench.benchmark_dir} -s test-solver --no-plot".split(),
            'benchopt', standalone_mode=False
        )

        # Check that completion also works
        _test_shell_completion(
            run_cmd, f"{bench.benchmark_dir} -s".split(),
            [("", ['test-solver', 'my-solver'])]
        )
