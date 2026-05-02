import pytest

from benchopt.cli.main import run
from benchopt.results import read_results
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.tests.utils import CaptureCmdOutput


def test_objective_bad_name(no_debug_log):
    # Check that if Objective.evaluate_result return a `name` field, a sensible
    # error is raised.

    objective = """from benchopt.utils.temp_benchmark import TempObjective

        class Objective(TempObjective):
            name = "test_obj"
            def evaluate_result(self, beta): return dict(value=1, name=0)
    """

    with temp_benchmark(objective=objective) as bench:
        with CaptureCmdOutput(exit=1) as out:
            run(
                f"{bench.benchmark_dir} -d test-dataset --no-plot".split(),
                standalone_mode=False
            )

    out.check_output("ValueError: objective output cannot contain 'name' key")


def test_objective_no_value(no_debug_log):
    # Check that if Obejctive.evaluate_result does not return a `value` field,
    # a sensible error is raised.

    objective = """from benchopt.utils.temp_benchmark import TempObjective

        class Objective(TempObjective):
            name = "test_obj"
            def evaluate_result(self, beta): return dict(test_acc=0)
    """

    solver = """from benchopt.utils.temp_benchmark import TempSolver
    from benchopt.stopping_criterion import SufficientProgressCriterion

    class Solver(TempSolver):
        name = "test-solver"
        #STOP
    """

    with temp_benchmark(objective=objective, solvers=solver) as bench:
        with CaptureCmdOutput(exit=1) as out:
            run(
                f"{bench.benchmark_dir} -d test-dataset --no-plot".split(),
                standalone_mode=False
            )

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
            run(
                f"{bench.benchmark_dir} -d test-dataset --no-plot".split(),
                standalone_mode=False
            )

    out.check_output(
        r"Objective.evaluate_result\(\) should contain a key named 'XXX'"
    )

    # Check that there is no error if the key is present or if using
    # a solver with strategy run_once.
    solver_run_once = solver.replace(
        "#STOP", "sampling_strategy = 'run_once'"
    )
    for solver in [solver_run_once, solver_key.replace('XXX', 'test_acc')]:
        with temp_benchmark(objective=objective, solvers=solver) as bench:
            with CaptureCmdOutput() as out:
                run(
                    f"{bench.benchmark_dir} -d test-dataset -n 1 --no-plot"
                    .split(), standalone_mode=False
                )

        out.check_output("done")


def test_objective_nonnumeric_values(no_debug_log):
    # Non-primitive objective values (dicts, numpy arrays) are serialized
    # inline into the parquet file via pack()/unpack(). No warning should be
    # raised and the result file should be a parquet, not a CSV fallback.

    objective = """from benchopt.utils.temp_benchmark import TempObjective

        class Objective(TempObjective):
            name = "test_obj"
            def evaluate_result(self, beta):
                return dict(value=1, test_obj={'a': 0, 'b': 1.0, 'c': ''})
    """

    import warnings
    with temp_benchmark(objective=objective) as bench:
        with CaptureCmdOutput(delete_result_files=False) as out:
            with warnings.catch_warnings():
                warnings.simplefilter("error", UserWarning)
                run(
                    f"{bench.benchmark_dir} -d test-dataset -n 1 --no-plot"
                    .split(), standalone_mode=False
                )
        assert out.result_files[0].endswith('.parquet')

    objective = """from benchopt.utils.temp_benchmark import TempObjective
        import numpy as np

        class Objective(TempObjective):
            name = "test_obj"
            def evaluate_result(self, beta):
                return dict(value=1, frame=np.zeros((4, 4)))
    """

    with temp_benchmark(objective=objective) as bench:
        with CaptureCmdOutput(delete_result_files=False) as out:
            with warnings.catch_warnings():
                warnings.simplefilter("error", UserWarning)
                run(
                    f"{bench.benchmark_dir} -d test-dataset -n 1 --no-plot"
                    .split(), standalone_mode=False
                )
        assert out.result_files[0].endswith('.parquet')


@pytest.mark.parametrize("n_rep", [1, 3])
@pytest.mark.parametrize("n_it", [1, 3])
def test_objective_multiple_points(n_rep, n_it):
    # Check that if Objective.evaluate_result returns a list, we get
    # multiple points in the final DataFrame.
    n_out = 3
    objective = f"""from benchopt.utils.temp_benchmark import TempObjective

        class Objective(TempObjective):
            name = "test_obj"
            def evaluate_result(self, beta):
                return [dict(value=i) for i in range({n_out})]
    """

    with temp_benchmark(objective=objective) as bench:
        with CaptureCmdOutput(delete_result_files=False) as out:
            run(
                f"{bench.benchmark_dir} -d test-dataset --no-plot "
                f"-r {n_rep} -n {n_it}".split(), standalone_mode=False
            )
        df = read_results(out.result_files[0])

    assert len(df) == n_out * n_rep * (n_it+1), out.output
    assert df['objective_value'].unique().tolist() == [0, 1, 2]
    assert df['idx_rep'].unique().tolist() == list(range(n_rep))
    assert df['stop_val'].unique().tolist() == [0, 1, 2, 4][:n_it + 1]
