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
                def prepare(self): print("#PREPARED")
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
            .replace('#PREPARED', '#SKIPPED')
        )
        with temp_benchmark(datasets=[self.dataset, ds_b]) as bench:
            with CaptureCmdOutput() as out:
                prepare_cmd(
                    f"{bench.benchmark_dir} -d dataset".split(),
                    'benchopt', standalone_mode=False
                )
            out.check_output("#PREPARED", repetition=1)
            out.check_output("#GET_DATA", repetition=0)
            out.check_output("#SKIPPED", repetition=0)

    def test_default_fallback_calls_get_data(self):
        """Without a custom prepare(), get_data() is called as fallback."""
        dataset = self.dataset.replace(
            "def prepare(self): print(\"#PREPARED\")", ""
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
            out.check_output("#PREPARED", repetition=1)

    def test_cache_ignore_deduplicates(self):
        """prepare_cache_ignore collapses correctly ignore params."""
        dataset = """from benchopt import BaseDataset
            class Dataset(BaseDataset):
                name = "dataset"
                parameters = {'n': [1, 2], 'seed': [0, 1, 2]}
                prepare_cache_ignore = ('seed',)
                def prepare(self): print(
                    f"#PREPARED({self.n}, {self.seed})"
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
            out.check_output("#PREPARED", repetition=2)
            out.check_output(r"#PREPARED\(1, 0\)", repetition=1)
            out.check_output(r"#PREPARED\(2, 0\)", repetition=1)

            f = bench.benchmark_dir / "prep_config.yml"
            f.write_text(
                "dataset:\n  dataset:\n    n: [3, 4]\n"
                "    seed: [42, 124, 23]\n"
            )
            with CaptureCmdOutput() as out:
                prepare_cmd(
                    [str(bench.benchmark_dir), "--config", str(f)],
                    'benchopt', standalone_mode=False
                )
            # 2 values of n x 3 values of seed = 6 combos, but seed is ignored
            # -> only 2 unique effective combos -> prepare() called twice
            out.check_output("#PREPARED", repetition=2)
            out.check_output(r"#PREPARED\(3, 0\)", repetition=1)
            out.check_output(r"#PREPARED\(4, 0\)", repetition=1)

    @pytest.mark.parametrize('n_jobs', [1, 2])
    def test_valid_call(self, n_jobs):
        """Parallel prepare runs the preparation in parallel."""
        datasets = [
            self.dataset,
            self.dataset.replace('dataset', 'dataset-b')
            .replace('#PREPARED', '#B_PREPARED'),
        ]
        with temp_benchmark(datasets=datasets) as bench:
            with CaptureCmdOutput() as out:
                prepare_cmd(
                    f"{bench.benchmark_dir} -j {n_jobs}".split(),
                    'benchopt', standalone_mode=False
                )
            # Both datasets must appear in progress output
            out.check_output("Preparing dataset ")
            out.check_output("Preparing dataset-b ")
            out.check_output("#PREPARED", repetition=1)
            out.check_output("#B_PREPARED", repetition=1)
            out.check_output("Summary: 2/2 datasets ready.")

    @pytest.mark.parametrize('n_jobs', [1, 2])
    def test_failure_dont_block_others(self, n_jobs):
        """Failed prepare() exits with code 1 and prints the traceback."""
        datasets = [
            self.dataset.replace(
                'print("#PREPARED")',
                'raise RuntimeError("failure info")'
            ).replace('dataset', 'invalid'),
            self.dataset,
        ]
        with temp_benchmark(datasets=datasets) as bench:
            with CaptureCmdOutput(exit=1) as out:
                prepare_cmd(
                    [str(bench.benchmark_dir), "-j", str(n_jobs)],
                    'benchopt', standalone_mode=False
                )
        out.check_output("failure info")
        out.check_output("FAILED")
        out.check_output("#PREPARED", repetition=1)
        out.check_output("1/2 datasets ready", repetition=1)

    def test_get_seed_dataset_ok(self):
        """get_data() may call get_seed(use_dataset=True) during prepare."""
        dataset = """from benchopt import BaseDataset
            class Dataset(BaseDataset):
                name = "dataset"
                def get_data(self):
                    print('#SEED=', self.get_seed(use_dataset=True))
                    return dict(X=0, y=1)
        """
        with temp_benchmark(datasets=dataset) as bench:
            with CaptureCmdOutput() as out:
                prepare_cmd(
                    [str(bench.benchmark_dir)],
                    'benchopt', standalone_mode=False
                )
            out.check_output(r"#SEED=", repetition=1)
            out.check_output("Summary: 1/1 datasets ready.")

    @pytest.mark.parametrize('seed_arg', [
        'use_objective=True', 'use_solver=True', 'use_repetition=True',
    ])
    def test_get_seed_non_dataset_raises(self, seed_arg):
        """get_seed() depending on objective/solver/rep fails in prepare.

        These dimensions are unknown at preparation time, so prepare must fail
        with a clear error instead of the run_context-not-initialized error.
        """
        dataset = f"""from benchopt import BaseDataset
            class Dataset(BaseDataset):
                name = "dataset"
                def get_data(self):
                    self.get_seed({seed_arg})
                    return dict(X=0, y=1)
        """
        with temp_benchmark(datasets=dataset) as bench:
            with CaptureCmdOutput(exit=1) as out:
                prepare_cmd(
                    [str(bench.benchmark_dir)],
                    'benchopt', standalone_mode=False
                )
        out.check_output("is defined in the current run context")
        out.check_output("FAILED")

    def test_seed_passed_to_get_seed(self):
        """The --seed value controls the seed available during prepare."""
        dataset = """from benchopt import BaseDataset
            class Dataset(BaseDataset):
                name = "dataset"
                def get_data(self):
                    print('#SEED=', self.get_seed(use_dataset=True))
                    return dict(X=0, y=1)
        """
        seeds = []
        with temp_benchmark(datasets=dataset) as bench:
            for seed in [0, 1]:
                with CaptureCmdOutput() as out:
                    prepare_cmd(
                        f"{bench.benchmark_dir} --seed {seed}".split(),
                        'benchopt', standalone_mode=False
                    )
                seeds += out.check_output(r"#SEED= (\d+)", repetition=1)
        assert seeds[0] != seeds[1]

    def test_cache_per_seed(self):
        """Prepare cached per-seed: same seed hits cache, new seed re-runs."""
        dataset = """from benchopt import BaseDataset
            class Dataset(BaseDataset):
                name = "dataset"
                def prepare(self):
                    print('#PREPARED', self.get_seed(use_dataset=True))
                def get_data(self): return dict(X=0, y=1)
        """
        with temp_benchmark(datasets=dataset) as bench:
            # Same seed twice: prepare runs once, second call hits the cache.
            with CaptureCmdOutput() as out:
                prepare_cmd(
                    f"{bench.benchmark_dir} --seed 0".split(),
                    'benchopt', standalone_mode=False
                )
                prepare_cmd(
                    f"{bench.benchmark_dir} --seed 0".split(),
                    'benchopt', standalone_mode=False
                )
            out.check_output("#PREPARED", repetition=1)

            # A different seed invalidates the cache and re-runs prepare.
            with CaptureCmdOutput() as out:
                prepare_cmd(
                    f"{bench.benchmark_dir} --seed 1".split(),
                    'benchopt', standalone_mode=False
                )
            out.check_output("#PREPARED", repetition=1)

    def test_force_flag(self, tmp_path):
        """--force re-runs preparation even when cached."""
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
            out.check_output("#PREPARED", repetition=2)
