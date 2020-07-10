import uuid
import pytest

from benchopt.config import DEFAULT_GLOBAL
from benchopt.utils.shell_cmd import delete_conda_env
from benchopt.utils.shell_cmd import create_conda_env


DEFAULT_GLOBAL['debug'] = True
DEFAULT_GLOBAL['raise_install_error'] = True

_clean_env = False
_TEST_ENV_NAME = None


def pytest_addoption(parser):
    parser.addoption("--skip-install", action="store_true",
                     help="skip install of solvers that can slow down CI.")
    parser.addoption("--test-env", type=str, default=None,
                     help="Use a given env to test the solvers' install.")
    parser.addoption("--recreate", action="store_true",
                     help="Recreate the environment if it already exists.")


def pytest_configure(config):
    """Setup pytest for benchopt testing"""

    config.addinivalue_line("markers", "requires_install")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--skip-install"):
        return

    skip_install = pytest.mark.skip(
            reason="--skip-install option provided")
    for item in items:
        if "requires_install" in item.keywords:
            item.add_marker(skip_install)


@pytest.fixture
def test_env_name(request):
    global _TEST_ENV_NAME, _clean_env

    if _TEST_ENV_NAME is None:
        env_name = request.config.getoption("--test-env")
        recreate = request.config.getoption("--recreate")
        if env_name is None:
            _clean_env = True
            env_name = f"_benchopt_test_env_{uuid.uuid4()}"

        _TEST_ENV_NAME = env_name

        create_conda_env(_TEST_ENV_NAME, recreate=recreate)

    return _TEST_ENV_NAME


@pytest.fixture(scope='session', autouse=True)
def delete_test_env():
    global _TEST_ENV_NAME

    if _TEST_ENV_NAME is not None and _clean_env:
        delete_conda_env(_TEST_ENV_NAME)
