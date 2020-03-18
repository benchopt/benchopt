import pytest

from benchopt.config import DEFAULT_GLOBAL


DEFAULT_GLOBAL['debug'] = True
DEFAULT_GLOBAL['print_install_error'] = True


def pytest_addoption(parser):
    parser.addoption("--skip-install", action="store_true",
                     help="skip install of solvers that can slow down CI.")


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
