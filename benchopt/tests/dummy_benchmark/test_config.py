import sys

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

    # R-PGD solver needs R to be added manually to path
    # https://stackoverflow.com/questions/63863449/oserror-cannot-load-library-c-program-files-r-r-4-0-2-bin-x64-r-dll-error-0
    if 'r-pgd' in solver_class.name.lower() and sys.platform == 'win32':
        pytest.xfail('R-PGD is not easy to install on Windows.')
