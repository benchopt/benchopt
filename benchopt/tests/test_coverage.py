import os
from benchopt.utils.shell_cmd import _run_shell_in_conda_env


def _test_coverage():
    import coverage
    assert coverage.Coverage.current() is not None, (
        f"coverage is not started: {os.environ.get('COVERAGE_PROCESS_START')}"
    )


def test_coverage(test_env_name):
    if os.environ.get('COVERAGE_PROCESS_START') is None:
        import pytest
        pytest.skip("Coverage not running")

    _test_coverage()

    _run_shell_in_conda_env(
        "python -c 'from benchopt.tests.test_coverage import _test_coverage;"
        " _test_coverage()'",
        env_name=test_env_name, raise_on_error=True
    )
