import os

# Make sure that R_HOME is loaded from the current interpreter to avoid
# using the parent interpreter R_HOME in the sub-interpreter.
if os.environ.get('R_HOME', None) is not None:
    del os.environ['R_HOME']


import rpy2  # noqa: E402
import rpy2.robjects.packages as rpackages  # noqa: E402
from rpy2.robjects.packages import PackageNotInstalledError  # noqa: E402

# Hide the R warnings
rpy2.robjects.r['options'](warn=-1)


def import_rpackages(*packages):
    """Helper to import R packages in the import_ctx"""
    for pkg in packages:
        try:
            rpackages.importr(pkg)
        except PackageNotInstalledError:
            raise ImportError(f"R package '{pkg}' is not installed")
