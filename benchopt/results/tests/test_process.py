import pytest

from benchopt.results.process import merge_results
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.tests.utils.capture_cmd_output import CaptureCmdOutput
from benchopt.cli.main import run


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

        df = merge_results(result_files)
        # n_rep runs, n_it + 1 entries.
        # 1 dataset for first run, 2 datasets for second run
        assert len(df) == n_rep * (1 + n_it) * (1 + 2)

        df = merge_results(result_files, overwrite=True)
        # with overwrite, first run dataset is overritten by second run
        assert len(df) == n_rep * (1 + n_it) * 2
