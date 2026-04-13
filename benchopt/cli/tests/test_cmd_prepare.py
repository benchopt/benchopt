import re

import click
import pytest

from benchopt.cli.main import prepare as prepare_cmd
from benchopt.tests.utils import CaptureCmdOutput
from benchopt.utils.temp_benchmark import temp_benchmark


class TestPrepareCmd:

    dataset = """from benchopt import BaseDataset
            class Dataset(BaseDataset):
                name = "dataset"
                def prepare(self): print("#PREPRARED")
                def get_data(self): print("#GET_DATA")
        """

    @pytest.mark.parametrize('invalid_benchmark, match', [
        ('invalid_benchmark', "Path 'invalid_benchmark' does not exist."),
        ('.', "The folder '.' does not contain `objective.py`")],
        ids=['invalid_path', 'no_objective'])
    def test_invalid_benchmark(self, invalid_benchmark, match):
        with pytest.raises(click.BadParameter, match=re.escape(match)):
            prepare_cmd(
                [invalid_benchmark], 'benchopt', standalone_mode=False
            )

    def test_basic_invocation(self):
        """benchopt prepare runs without error on a default benchmark."""
        with temp_benchmark() as bench, CaptureCmdOutput() as out:
            prepare_cmd(
                f"{bench.benchmark_dir}".split(),
                'benchopt', standalone_mode=False
            )
        out.check_output(f"Preparing datasets for benchmark '{bench.name}'")

    def test_dataset_filter(self, tmp_path):
        """Only the selected dataset is prepared when -d is used."""

        ds_b = (
            self.dataset.replace('dataset', 'dataset-filtered')
            .replace('#PREPRARED', '#SKIPPED')
        )
        with temp_benchmark(datasets=[self.dataset, ds_b]) as bench:
            with CaptureCmdOutput() as out:
                prepare_cmd(
                    f"{bench.benchmark_dir} -d dataset".split(),
                    'benchopt', standalone_mode=False
                )
            out.check_output("#PREPRARED", repetition=1)
            out.check_output("#GET_DATA", repetition=0)
            out.check_output("#SKIPPED", repetition=0)

    def test_default_fallback_calls_get_data(self):
        """Without a custom prepare(), get_data() is called as fallback."""
        dataset = self.dataset.replace(
            "def prepare(self): print(\"#PREPRARED\")", ""
        )
        with temp_benchmark(datasets=dataset) as bench:
            with CaptureCmdOutput() as out:
                prepare_cmd(
                    [str(bench.benchmark_dir)],
                    'benchopt', standalone_mode=False
                )
            out.check_output("#GET_DATA", repetition=1)

    def test_caching_skips_second_call(self):
        """Second prepare call hits the cache and does not re-run prepare()."""
        with temp_benchmark(datasets=self.dataset) as bench:
            with CaptureCmdOutput() as out:
                prepare_cmd(
                    [str(bench.benchmark_dir)],
                    'benchopt', standalone_mode=False
                )
                prepare_cmd(
                    [str(bench.benchmark_dir)],
                    'benchopt', standalone_mode=False
                )
            out.check_output("#PREPRARED", repetition=1)

    def test_cache_ignore_deduplicates(self):
        """prepare_cache_ignore collapses correctly ignore params."""
        dataset = """from benchopt import BaseDataset
            class Dataset(BaseDataset):
                name = "dataset"
                parameters = {'n': [1, 2], 'seed': [0, 1, 2]}
                prepare_cache_ignore = ('seed',)
                def prepare(self): print(
                    f"#PREPRARED({self.n}, {self.seed})"
                )
                def get_data(self): return dict(X=None, y=None)
        """
        with temp_benchmark(datasets=dataset) as bench:
            with CaptureCmdOutput() as out:
                prepare_cmd(
                    [str(bench.benchmark_dir)],
                    'benchopt', standalone_mode=False
                )
            # 2 values of n x 3 values of seed = 6 combos, but seed is ignored
            # -> only 2 unique effective combos -> prepare() called twice
            out.check_output("#PREPRARED", repetition=2)
            out.check_output(r"#PREPRARED\(1, 0\)", repetition=1)
            out.check_output(r"#PREPRARED\(2, 0\)", repetition=1)

    def test_failure_exits_nonzero_and_warns(self):
        """Failed prepare() exits with code 1 and prints the traceback."""
        dataset = self.dataset.replace(
            'print("#PREPRARED")',
            'raise RuntimeError("preparation failed")'
        )
        with temp_benchmark(datasets=dataset) as bench:
            with CaptureCmdOutput(exit=1) as out:
                prepare_cmd(
                    [str(bench.benchmark_dir)],
                    'benchopt', standalone_mode=False
                )
        out.check_output("preparation failed")

    def test_force_flag(self, tmp_path):
        """--force re-runs preparation even when cached."""
        counter_file = tmp_path / "count.txt"
        counter_file.write_text("0")
        with temp_benchmark(datasets=self.dataset) as bench:
            with CaptureCmdOutput() as out:
                prepare_cmd(
                    [str(bench.benchmark_dir)],
                    'benchopt', standalone_mode=False
                )
                prepare_cmd(
                    f"{bench.benchmark_dir} --force".split(),
                    'benchopt', standalone_mode=False
                )
            out.check_output("#PREPRARED", repetition=2)
