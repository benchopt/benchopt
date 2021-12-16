import sys

import pytest


def check_test_solver_install(solver_class):

    if solver_class.name.lower() == 'cyanure' and sys.platform == 'darwin':
        pytest.xfail('Cyanure is not easy to install on macos.')

    # Skip test_solver_install for julia in OSX as there is a version
    # conflict with conda packages for R
    # See issue #64
    # julia=1.6.4 broke on conda, see PR #252
    if 'julia' in solver_class.name.lower():
        # pytest.xfail('Julia causes segfault on OSX for now.')
        pytest.xfail('Julia install via conda is broken for now.')
