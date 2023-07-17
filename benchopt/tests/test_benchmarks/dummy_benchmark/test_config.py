import sys
from shutils import which
import pytest


def check_test_solver_install(solver_class):

    if solver_class.name.lower() == 'cyanure' and sys.platform == 'darwin':
        pytest.xfail('Cyanure is not easy to install on macos.')

    # Skip test_solver_install for julia in OSX as there is a version
    # conflict with conda packages for R
    # See issue #64
    if 'julia' in solver_class.name.lower() and sys.platform == 'darwin':
        pytest.xfail('Julia causes segfault on OSX for now.')

    if solver_class.name.lower() in ["solver-test"]:
        pytest.skip('Test solver that cannot be installed, skipping.')

    if 'matlab' in solver_class.name.lower() and which('matlab') is None:
        pytest.skip('Matlab not testable in CI, skipping.')
