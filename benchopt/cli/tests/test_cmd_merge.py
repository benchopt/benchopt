import pytest

from benchopt.cli.main import run
from benchopt.cli.process_results import merge
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.tests.utils import CaptureCmdOutput
from benchopt.results import read_results


class TestCmdMerge:
    @pytest.mark.parametrize("n_rep", [0, 1])
    @pytest.mark.parametrize("ext", ["default", "parquet", "csv"])
    def test_merge_results(self, ext, n_rep):
        ext = ".parquet" if ext == "default" else f".{ext}"
        with temp_benchmark() as bench:
            with CaptureCmdOutput(delete_result_files=False) as out:
                command = f"{bench.benchmark_dir} -d test-dataset --no-plot "

                cmd = f"{command} -n 1 --output unique_name"
                run(cmd.split(), 'benchopt', standalone_mode=False)
                cmd = f"{command} -n {n_rep} --output unique_name_2{ext}"
                run(cmd.split(), 'benchopt', standalone_mode=False)

            run_date_1 = read_results(out.result_files[0])["run_date"].unique()
            run_date_2 = read_results(out.result_files[1])["run_date"].unique()

            # Check merge without overwrite
            with CaptureCmdOutput(delete_result_files=False) as out_merge:
                merge(
                    f"{bench.benchmark_dir} -f {out.result_files[0]} -f"
                    f"{out.result_files[1]} --output merged_results.parquet"
                    .split(), standalone_mode=False,
                )
            assert len(out_merge.result_files) == 1
            assert "merged_results.parquet" in out_merge.result_files[0]
            df = read_results(out_merge.result_files[0])
            assert len(df) == 3 + n_rep
            assert df["run_date"].nunique() == 2
            assert set(df["run_date"]) == set((*run_date_1, *run_date_2))

            # Check merge with overwrite
            with CaptureCmdOutput(delete_result_files=False) as out_merge:
                merge(
                    f"{bench.benchmark_dir} -f {out.result_files[0]} -f"
                    f"{out.result_files[1]} --output merged_results_1.parquet "
                    "--overwrite"
                    .split(), standalone_mode=False,
                )
            df = read_results(out_merge.result_files[0])
            assert len(df) == 2

            expected_runs = 1 if n_rep == 1 else 2
            assert df["run_date"].nunique() == expected_runs
            s_val0 = df.query("stop_val == 0")["run_date"].unique()
            assert len(s_val0) == 1
            assert s_val0[0] == run_date_2[0]
            if expected_runs == 1:
                assert df["run_date"].iloc[0] == run_date_2
