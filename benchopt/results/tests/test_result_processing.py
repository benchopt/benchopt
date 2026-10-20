import pytest

from benchopt.results import read_results
from benchopt.results.result_processing import describe_results, merge_results
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.tests.utils.capture_cmd_output import CaptureCmdOutput
from benchopt.cli.main import run


OBJECTIVE_WITH_EXTRA_METRIC = """from benchopt import BaseObjective

    class Objective(BaseObjective):
        name = "test-objective"
        def set_data(self, X, y): pass
        def get_one_result(self): return dict(beta=None)
        def evaluate_result(self, beta):
            return dict(value=1., train_loss=0.5)
        def get_objective(self): return dict(X=None, y=None, lmbd=None)
"""


@pytest.mark.parametrize('n_rep, n_it', [(2, 0), (4, 1)])
def test_merge_results(n_rep, n_it):
    with temp_benchmark() as bench:
        with CaptureCmdOutput(delete_result_files=False) as out:
            run(
                f"{bench.benchmark_dir} -r {n_rep} -n {n_it} --no-plot "
                "-d simulated --output test".split(), standalone_mode=False
            )
        with CaptureCmdOutput(delete_result_files=False) as out2:
            run(
                f"{bench.benchmark_dir} -r {n_rep} -n {n_it} --no-plot "
                "--output test2".split(),
                standalone_mode=False
            )

        result_files = out.result_files + out2.result_files
        assert len(result_files) == 2

        df = merge_results(result_files, keep="all")
        # n_rep runs, n_it + 1 entries.
        # 1 dataset for first run, 2 datasets for second run
        assert len(df) == n_rep * (1 + n_it) * (1 + 2)

        df = merge_results(result_files, keep="last")
        # with keep="last", first run dataset is overritten by second run
        assert len(df) == n_rep * (1 + n_it) * 2


def test_describe_results_on_generated_file():
    # describe_results summarizes a real result file produced by
    # `benchopt run`.
    with temp_benchmark(objective=OBJECTIVE_WITH_EXTRA_METRIC) as bench:
        with CaptureCmdOutput(delete_result_files=False) as out:
            run(
                f"{bench.benchmark_dir} -d test-dataset -n 0 -r 2 "
                "--no-plot".split(), standalone_mode=False
            )
        result_file = out.result_files[0]

        summary = describe_results(result_file)

    assert summary["n_rows"] == 2
    assert summary["n_configs"] == 1
    assert summary["n_repetitions"] == 2
    assert summary["objectives"] == ["test-objective"]
    assert summary["solvers"] == ["test-solver"]
    assert summary["datasets"] == ["test-dataset"]
    assert summary["objective_columns"] == [
        "objective_value", "objective_train_loss"
    ]
    assert len(summary["run_dates"]) == 1


def test_describe_results_accepts_dataframe():
    # describe_results also accepts an already-loaded DataFrame, avoiding
    # a re-read from disk.
    with temp_benchmark() as bench:
        with CaptureCmdOutput(delete_result_files=False) as out:
            run(
                f"{bench.benchmark_dir} -d test-dataset -n 1 -r 1 "
                "--no-plot".split(), standalone_mode=False
            )
        df = read_results(out.result_files[0])

    summary = describe_results(df)
    assert summary["n_rows"] == len(df)
    assert summary["n_configs"] == 1
