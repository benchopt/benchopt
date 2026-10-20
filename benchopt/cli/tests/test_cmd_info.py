import re
import click
import pytest
from pathlib import Path

from benchopt.utils.temp_benchmark import temp_benchmark

from benchopt.tests.utils import CaptureCmdOutput

from benchopt.cli.main import run
from benchopt.cli.helpers import info


DATASET_WITH_CHOICES = """from benchopt import BaseDataset

    class Dataset(BaseDataset):
        name = "with-choices"
        parameters = {'param': ['a']}

        @classmethod
        def get_all_parameter_values(cls, name):
            if name == 'param':
                return ['a', 'b', 'c']
            return super().get_all_parameter_values(name)

        def get_data(self): return dict(X=0)
"""

DATASET_NO_CHOICES = """from benchopt import BaseDataset

    class Dataset(BaseDataset):
        name = "no-choices"
        parameters = {'param': ['a']}

        def get_data(self): return dict(X=0)
"""

OBJECTIVE_WITH_MIN_VERSION = """from benchopt import BaseObjective

    class Objective(BaseObjective):
        name = "with-min-version"
        min_benchopt_version = "{min_version}"
        def set_data(self, X, y): pass
        def get_one_result(self): return dict(beta=None)
        def evaluate_result(self, beta): return 1.
        def get_objective(self): return dict(X=None, y=None, lmbd=None)
"""


class TestCmdInfo:
    def test_info_lists_choices(self):
        # `benchopt info` lists the values declared by
        # get_all_parameter_values, with a total count.
        with temp_benchmark(datasets=[DATASET_WITH_CHOICES]) as bench:
            with CaptureCmdOutput() as out:
                info(
                    [str(bench.benchmark_dir), '-d', 'with-choices'],
                    'benchopt', standalone_mode=False
                )

        out.check_output("param: a", repetition=1)
        out.check_output(r"valid values: a, b, c \(3 total\)", repetition=1)

    def test_info_no_choices(self):
        # Without the hook, `info` does not print a "valid values" line.
        with temp_benchmark(datasets=[DATASET_NO_CHOICES]) as bench:
            with CaptureCmdOutput() as out:
                info(
                    [str(bench.benchmark_dir), '-d', 'no-choices'],
                    'benchopt', standalone_mode=False
                )

        out.check_output("param: a", repetition=1)
        out.check_output("valid values", repetition=0)

    def test_info_version_compatible(self):
        # `info --version` exits cleanly when benchopt is recent enough.
        objective = OBJECTIVE_WITH_MIN_VERSION.format(min_version="0.0.0")
        with temp_benchmark(objective=objective) as bench:
            with CaptureCmdOutput() as out:
                info([str(bench.benchmark_dir), '--version'],
                     'benchopt', standalone_mode=False)
        out.check_output("satisfies the requirement", repetition=1)

    def test_info_version_incompatible(self):
        # `info --version` raises (non-zero exit) when benchopt is too old.
        objective = OBJECTIVE_WITH_MIN_VERSION.format(min_version="99.9")
        with temp_benchmark(objective=objective) as bench:
            with pytest.raises(click.ClickException, match="too old"):
                info([str(bench.benchmark_dir), '--version'],
                     'benchopt', standalone_mode=False)

    def test_info_no_result_files_omits_section(self):
        # Without any prior run, the result files section is skipped.
        with temp_benchmark() as bench:
            with CaptureCmdOutput() as out_info:
                info([str(bench.benchmark_dir)], 'benchopt',
                     standalone_mode=False)

        out_info.check_output("# RESULT FILES", repetition=0)


class TestCmdInfoResultFiles:
    """Tests that read back result files, sharing one benchmark + 2 runs."""

    @classmethod
    def setup_class(cls):
        "Create one benchmark with two result files, reused by every test."
        cls.ctx = temp_benchmark()
        cls.bench = cls.ctx.__enter__()
        with CaptureCmdOutput(delete_result_files=False) as out:
            for output, n_rep in [('run_1', 2), ('run_2', 1)]:
                run(
                    [str(cls.bench.benchmark_dir), '-d', 'test-dataset',
                     '--no-plot', '-n', '0', '-r', str(n_rep),
                     '--output', output],
                    'benchopt', standalone_mode=False
                )
        assert len(out.result_files) == 2, out
        cls.result_files = {Path(f).stem: f for f in out.result_files}

    @classmethod
    def teardown_class(cls):
        "Clean up the temp benchmark directory."
        cls.ctx.__exit__(None, None, None)

    def test_info_filename_summarizes_result_file(self):
        # `benchopt info -f <file>` summarizes a result file instead of
        # listing the benchmark's solvers/datasets.
        with CaptureCmdOutput() as out_info:
            info(
                [str(self.bench.benchmark_dir),
                 '-f', self.result_files['run_1']],
                'benchopt', standalone_mode=False
            )

        out_info.check_output("Rows: 2", repetition=1)
        out_info.check_output(
            r"Configs \(objective x solver x dataset\): 1", repetition=1
        )
        out_info.check_output("Repetitions: 2", repetition=1)
        out_info.check_output(
            r"Objectives \(1\): test-objective", repetition=1
        )
        out_info.check_output(r"Solvers \(1\): test-solver", repetition=1)
        out_info.check_output(r"Datasets \(1\): test-dataset", repetition=1)
        out_info.check_output("# DATASETS", repetition=0)

    def test_info_filename_all_summarizes_every_result_file(self):
        # `benchopt info -f all` prints one summary block per result file
        # in the benchmark's output folder.
        with CaptureCmdOutput() as out_info:
            info(
                [str(self.bench.benchmark_dir), '-f', 'all'],
                'benchopt', standalone_mode=False
            )

        out_info.check_output(
            "Info regarding the result file", repetition=2
        )

    def test_info_filename_multiple_explicit_files(self):
        # `benchopt info -f file1 -f file2` summarizes each named file,
        # like multiple `-s`/`-d` options.
        with CaptureCmdOutput() as out_info:
            info(
                [str(self.bench.benchmark_dir),
                 '-f', self.result_files['run_1'],
                 '-f', self.result_files['run_2']],
                'benchopt', standalone_mode=False
            )

        out_info.check_output(
            "Info regarding the result file", repetition=2
        )

    def test_info_lists_available_result_files(self):
        # Plain `benchopt info <bench>` lists the result files available
        # in the output folder, in addition to solvers/datasets.
        with CaptureCmdOutput() as out_info:
            info([str(self.bench.benchmark_dir)], 'benchopt',
                 standalone_mode=False)

        out_info.check_output("# RESULT FILES", repetition=1)
        for result_file in self.result_files.values():
            out_info.check_output(
                re.escape(f"- {Path(result_file).name}"), repetition=1
            )
