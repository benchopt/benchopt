from pytest import fixture

from benchopt.util import create_venv, delete_venv
from benchopt.config import DEFAULT_GLOBAL
DEFAULT_GLOBAL['debug'] = True
DEFAULT_GLOBAL['print_install_error'] = True


# Setup and clean a test env to install/uninstall all the solvers and check
# that they are correctly configured

TEST_ENV_NAME = "benchopt_test_env"


@fixture
def test_env():
    return TEST_ENV_NAME


@fixture
def ensure_test_env():
    create_venv(TEST_ENV_NAME, recreate=True)
    yield
    delete_venv(TEST_ENV_NAME)
