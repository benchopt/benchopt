import re
import sys

import click
import pytest

from benchopt.utils.temp_benchmark import temp_benchmark


from benchopt.tests.utils import CaptureCmdOutput
from benchopt.utils.shell_cmd import _run_shell_in_conda_env

from benchopt.cli.main import test as benchopt_test

from benchopt.cli.tests.completion_cases import _test_shell_completion
from benchopt.cli.tests.completion_cases import (  # noqa: F401
    bench_completion_cases
)


class TestCmdTest:

    @pytest.mark.parametrize('invalid_benchmark, match', [
        ('invalid_benchmark', "Path 'invalid_benchmark' does not exist."),
        ('.', "The folder '.' does not contain `objective.py`")],
        ids=['invalid_path', 'no_objective'])
    def test_invalid_benchmark(self, invalid_benchmark, match):
        with pytest.raises(click.BadParameter, match=re.escape(match)):
            benchopt_test(
                [invalid_benchmark], 'benchopt', standalone_mode=False
            )

    def test_valid_call(self):
        with temp_benchmark() as bench, CaptureCmdOutput() as out:
            benchopt_test(
                f"{bench.benchmark_dir} --skip-install".split(),
                'benchopt', standalone_mode=False
            )

        out.check_output("test session starts", repetition=1)
        out.check_output("PASSED", repetition=8)
        out.check_output("SKIPPED", repetition=1)

    def test_valid_call_fail(self):
        solver = """
        from benchopt import BaseSolver
        class Solver(BaseSolver):
            name = "failing-solver"
            def set_objective(self, X, y, lmbd): pass
            def run(self, _): raise ValueError("Intentional Error")
            def get_result(self): return dict(beta=1)
        """
        with temp_benchmark(solvers=solver) as bench:
            exit_code = 1 if sys.platform == "win32" else 256
            with CaptureCmdOutput(exit=exit_code) as out:
                benchopt_test(
                    f"{bench.benchmark_dir} --skip-install".split(),
                    'benchopt', standalone_mode=False
                )

        out.check_output("test session starts", repetition=1)
        out.check_output("FAILED", repetition=2)
        out.check_output("PASSED", repetition=7)
        out.check_output("SKIPPED", repetition=1)

    def test_valid_call_in_env_no_pytest(self, test_env_name, no_pytest):
        with temp_benchmark() as bench:
            msg = f"pytest is not installed in conda env {test_env_name}"
            with pytest.raises(ModuleNotFoundError, match=msg):
                assert 1 == _run_shell_in_conda_env(
                    "which pytest", env_name=test_env_name
                )
                benchopt_test(
                   f"{bench.benchmark_dir} --env-name {test_env_name}".split(),
                   'benchopt', standalone_mode=False
                )

    def test_skip_test(self):
        test_config = """import pytest

        def check_test_dataset_get_data(benchmark, dataset):
            if dataset.name == "test-dataset":
                pytest.skip("skip for TEST")
        """

        with temp_benchmark(
            extra_files={'test_config.py': test_config}
        ) as bench, CaptureCmdOutput() as out:
            benchopt_test(
                f"{bench.benchmark_dir} -k dataset_get_data".split(),
                'benchopt', standalone_mode=False
            )

        out.check_output("test session starts", repetition=1)
        out.check_output("test_dataset_get_data", repetition=2)
        out.check_output("test_solver", repetition=0)
        out.check_output("PASSED", repetition=1)
        out.check_output("SKIPPED", repetition=1)

    def test_xfail_test(self):
        test_config = """import pytest

        def check_test_solver_run(benchmark, solver):
            pytest.xfail("xfail for TEST")
        """
        with temp_benchmark(
            extra_files={'test_config.py': test_config}
        ) as bench, CaptureCmdOutput() as out:
            benchopt_test(
                [str(bench.benchmark_dir), "-k", "test_solver_run"],
                'benchopt', standalone_mode=False
            )

        out.check_output("test session starts", repetition=1)
        out.check_output(r"test_solver_run\[", repetition=1)
        out.check_output("test_dataset_get_data", repetition=0)
        out.check_output("XFAIL", repetition=1)

    def test_deprecated_check_test_solver(self):
        test_config = """import pytest

        def check_test_solver(benchmark, solver):
            pytest.xfail("xfail for TEST")
        """
        with temp_benchmark(
            extra_files={'test_config.py': test_config}
        ) as bench, CaptureCmdOutput() as out:
            benchopt_test(
                [str(bench.benchmark_dir), "-k", "test_solver_run"],
                'benchopt', standalone_mode=False
            )
        out.check_output("XFAIL", repetition=1)

    def test_complete_bench(self, bench_completion_cases):  # noqa: F811

        # Completion for benchmark name
        _test_shell_completion(benchopt_test, [], bench_completion_cases)
