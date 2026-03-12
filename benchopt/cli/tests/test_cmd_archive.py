import re
import tarfile
from pathlib import Path

import click
import pytest

from benchopt.utils.temp_benchmark import temp_benchmark

from benchopt.tests.utils import CaptureCmdOutput

from benchopt.cli.main import run
from benchopt.cli.helpers import archive

from benchopt.cli.tests.completion_cases import (  # noqa: F401
    _test_shell_completion,
    bench_completion_cases
)


CURRENT_DIR = Path.cwd()


class TestArchiveCmd:

    @classmethod
    def setup_class(cls):
        "Make sure at least one result file is available"
        cls.ctx = temp_benchmark(extra_files={"README": ""})
        cls.bench = cls.ctx.__enter__()
        with CaptureCmdOutput(delete_result_files=False) as out:
            run(
                f"{cls.bench.benchmark_dir} -d test-dataset -n 2 -r 1 "
                "--no-plot".split(), 'benchopt', standalone_mode=False
            )
        assert len(out.result_files) == 1, out
        cls.result_file = out.result_files[0]

    @classmethod
    def teardown_class(cls):
        "Clean up the result file."
        cls.ctx.__exit__(None, None, None)

    @pytest.mark.parametrize('invalid_benchmark, match', [
        ('invalid_benchmark', "Path 'invalid_benchmark' does not exist."),
        ('.', "The folder '.' does not contain `objective.py`"),
        ("", rf"The folder '{CURRENT_DIR}' does not contain `objective.py`")],
        ids=['invalid_path', 'no_objective', "no_objective in default"])
    def test_invalid_benchmark(self, invalid_benchmark, match):
        with pytest.raises(click.BadParameter, match=re.escape(match)):
            if len(invalid_benchmark) > 0:
                archive([invalid_benchmark], 'benchopt', standalone_mode=False)
            else:
                archive([], 'benchopt', standalone_mode=False)

    def count_files_in_archive(self, archive_file):
        counts = {k: 0 for k in [
            "__pycache__", "outputs", "objective.py", "datasets",
            "solvers", "README"
        ]}

        with tarfile.open(archive_file, "r:gz") as tar:
            for elem in tar.getmembers():
                for k in counts:
                    counts[k] += k in elem.name
                assert elem.uname == "benchopt"
        return counts

    def test_call(self):

        with CaptureCmdOutput(delete_result_files=False) as out:
            archive([str(self.bench.benchmark_dir)], 'benchopt',
                    standalone_mode=False)

        try:
            assert len(out.result_files) == 1
            saved_file = out.result_files[0]
            counts = self.count_files_in_archive(saved_file)
        finally:
            # Make sure to clean up all files even when the test fails
            for f in out.result_files:
                Path(f).unlink()

        assert counts["README"] == 1, counts
        assert counts["objective.py"] == 1, counts
        assert counts["datasets"] >= 1, counts
        assert counts["solvers"] >= 1, counts
        assert counts["outputs"] == 0, counts
        assert counts["__pycache__"] == 0, counts

    def test_call_with_outputs(self):

        with CaptureCmdOutput(delete_result_files=False) as out:
            archive(f"{self.bench.benchmark_dir} --with-outputs".split(),
                    'benchopt', standalone_mode=False)
        saved_files = re.findall(r'Results are in (.*\.tar.gz)', out.output)
        try:
            assert len(out.result_files) == 1
            saved_file = out.result_files[0]
            counts = self.count_files_in_archive(saved_file)
        finally:
            # Make sure to clean up all files even when the test fails
            for f in saved_files:
                Path(f).unlink()

        assert counts["README"] == 1, counts
        assert counts["objective.py"] == 1, counts
        assert counts["datasets"] >= 1, counts
        assert counts["solvers"] >= 1, counts
        assert counts["outputs"] >= 1, counts
        assert counts["__pycache__"] == 0, counts

    def test_complete_bench(self, bench_completion_cases):  # noqa: F811
        # Completion for benchmark name
        _test_shell_completion(archive, [], bench_completion_cases)
