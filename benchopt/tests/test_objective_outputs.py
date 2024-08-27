import pytest

from benchopt.cli.main import run
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.tests.utils import CaptureRunOutput


MINIMAL_SOLVER = """from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = "test-solver"
        sampling_strategy = 'run_once'
        def set_objective(self, X, y): pass
        def run(self, n_iter): pass
        def get_result(self): return dict(beta=1)
    """


def test_objective_bad_name(no_debug_log):
    # Check that if Obejctive.evaluate_result return a `name` field, a sensible
    # error is raised.

    objective = """from benchopt import BaseObjective

        class Objective(BaseObjective):
            name = "test_obj"
            min_benchopt_version = "0.0.0"

            def set_data(self, X, y): pass
            def get_one_result(self): pass
            def evaluate_result(self, beta): return dict(value=1, name=0)
            def get_objective(self): return dict(X=0, y=0)
    """

    with temp_benchmark(
            objective=objective,
            solvers=[MINIMAL_SOLVER]
    ) as benchmark:
        with pytest.raises(SystemExit, match='1'):
            with CaptureRunOutput() as out:
                run([str(benchmark.benchmark_dir),
                    *'-s test-solver -d test-dataset -n 1 -r 1 --no-plot'
                    .split()], standalone_mode=False)

    out.check_output("ValueError: objective output cannot be called 'name'")


def test_objective_no_value(no_debug_log):
    # Check that if Obejctive.evaluate_result does not return a `value` field,
    # a sensible error is raised.

    objective = """from benchopt import BaseObjective

        class Objective(BaseObjective):
            name = "test_obj"
            min_benchopt_version = "0.0.0"

            def set_data(self, X, y): pass
            def get_one_result(self): pass
            def evaluate_result(self, beta): return dict(test_acc=0)
            def get_objective(self): return dict(X=0, y=0)
    """

    with temp_benchmark(
            objective=objective,
            solvers=[MINIMAL_SOLVER]
    ) as benchmark:
        with pytest.raises(SystemExit, match='1'):
            with CaptureRunOutput() as out:
                run([str(benchmark.benchmark_dir),
                    *'-s test-solver -d test-dataset -n 1 -r 1 --no-plot'
                    .split()], standalone_mode=False)

    out.check_output(
        r"Objective.evaluate_result\(\) should contain a key named 'value'"
    )


def test_objective_nonnumeric_values(no_debug_log):
    # Check that non-numerical values in objective do not raise error
    # in saving and generating the plots.

    objective = """from benchopt import BaseObjective

        class Objective(BaseObjective):
            name = "test_obj"
            min_benchopt_version = "0.0.0"

            def set_data(self, X, y): self.X, self.y = X, y
            def get_one_result(self): pass
            def evaluate_result(self, beta):
                return dict(value=1, test_obj={})

            def get_objective(self):
                return dict(X=0, y=0)
    """

    with temp_benchmark(
            objective=objective,
            solvers=[MINIMAL_SOLVER]
    ) as benchmark:
        with CaptureRunOutput() as out:
            run([str(benchmark.benchmark_dir),
                 *'-s test-solver -d test-dataset -n 1 -r 1 --no-display'
                 .split()], standalone_mode=False)

        assert out.result_files[0].endswith('.csv')

    objective = objective.replace(
        "test_obj={}", "test_obj={'a':0, 'b': 1.0, 'c': '', 'd': {}}"
    )
    with temp_benchmark(
            objective=objective,
            solvers=[MINIMAL_SOLVER]
    ) as benchmark:
        with CaptureRunOutput() as out:
            run([str(benchmark.benchmark_dir),
                 *'-s test-solver -d test-dataset -n 1 -r 1 --no-display'
                 .split()], standalone_mode=False)

        assert out.result_files[0].endswith('.csv')
