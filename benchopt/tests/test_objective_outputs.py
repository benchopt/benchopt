import pandas as pd

from benchopt.cli.main import run
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.tests.utils import CaptureCmdOutput


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

    with temp_benchmark(objective=objective, solvers=MINIMAL_SOLVER) as bench:
        with CaptureCmdOutput(exit=1) as out:
            run([str(bench.benchmark_dir),
                *'-s test-solver -d test-dataset -n 1 -r 1 --no-plot'.split()],
                standalone_mode=False)

    out.check_output("ValueError: objective output cannot contain 'name' key")


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

    solver = """from benchopt import BaseSolver
    from benchopt.stopping_criterion import SufficientProgressCriterion

    class Solver(BaseSolver):
        name = "test-solver"
        #STOP
        def set_objective(self, X, y): pass
        def run(self, n_iter): pass
        def get_result(self): return dict(beta=1)
    """

    with temp_benchmark(objective=objective, solvers=solver) as bench:
        with CaptureCmdOutput(exit=1) as out:
            run([str(bench.benchmark_dir),
                *'-s test-solver -d test-dataset -n 1 -r 1 --no-plot'
                .split()], standalone_mode=False)

    out.check_output(
        r"Objective.evaluate_result\(\) should contain a key named 'value'"
    )

    # check that the error is comprehensive when the key is missing
    solver_key = solver.replace(
        "#STOP",
        "stopping_criterion=SufficientProgressCriterion(key_to_monitor='XXX')"
    )
    with temp_benchmark(objective=objective, solvers=solver_key) as bench:
        with CaptureCmdOutput(exit=1) as out:
            run([str(bench.benchmark_dir),
                *'-s test-solver -d test-dataset -n 1 -r 1 --no-plot'
                .split()], standalone_mode=False)

    out.check_output(
        r"Objective.evaluate_result\(\) should contain a key named 'XXX'"
    )

    # Check that there is no error if the key is present or if using
    # a solver with strategy run_once.
    for solver in [MINIMAL_SOLVER, solver_key.replace('XXX', 'test_acc')]:
        with temp_benchmark(objective=objective, solvers=solver) as bench:
            with CaptureCmdOutput() as out:
                run([str(bench.benchmark_dir),
                    *'-s test-solver -d test-dataset -n 1 -r 1 --no-plot'
                    .split()], standalone_mode=False)

        out.check_output("done")


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

    with temp_benchmark(objective=objective, solvers=MINIMAL_SOLVER) as bench:
        with CaptureCmdOutput() as out:
            run([str(bench.benchmark_dir),
                 *'-s test-solver -d test-dataset -n 1 -r 1 --no-display'
                 .split()], standalone_mode=False)

        assert out.result_files[0].endswith('.csv')

    objective = objective.replace(
        "test_obj={}", "test_obj={'a':0, 'b': 1.0, 'c': '', 'd': {}}"
    )
    with temp_benchmark(objective=objective, solvers=MINIMAL_SOLVER) as bench:
        with CaptureCmdOutput() as out:
            run([str(bench.benchmark_dir),
                 *'-s test-solver -d test-dataset -n 1 -r 1 --no-display'
                 .split()], standalone_mode=False)

        assert out.result_files[0].endswith('.csv')


def test_objective_multiple_points(no_debug_log):
    # Check that if Objective.evaluate_result returns a list, we get
    # multiple points in the final DataFrame.

    objective = """from benchopt import BaseObjective

        class Objective(BaseObjective):
            name = "test_obj"
            min_benchopt_version = "0.0.0"

            def set_data(self, X, y): pass
            def get_one_result(self): pass
            def evaluate_result(self, beta):
                return [dict(value=i) for i in range(3)]
            def get_objective(self): return dict(X=0, y=0)
    """

    with temp_benchmark(objective=objective, solvers=MINIMAL_SOLVER) as bench:
        with CaptureCmdOutput(delete_result_files=False) as out:
            run([str(bench.benchmark_dir),
                *'-s test-solver -d test-dataset -n 1 -r 2 --no-plot'
                .split()], standalone_mode=False)
        df = pd.read_parquet(out.result_files[0])

    assert len(df) == 6
    assert df['objective_value'].unique().tolist() == [0, 1, 2]
    assert df['idx_rep'].unique().tolist() == [0, 1]
