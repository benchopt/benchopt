import os

# Make sure that R_HOME is loaded from the current interpreter to avoid
# using the parent interpreter R_HOME in the sub-interpreter.
if os.environ.get('R_HOME', None) is not None:
    del os.environ['R_HOME']

import rpy2  # noqa: E402
import rpy2.robjects.packages as rpackages  # noqa: E402
import rpy2.situation
try:
    from rpy2.robjects.packages import PackageNotInstalledError
except ImportError:
    # Backward compat for rpy2 version < 3.3
    try:
        from rpy2.rinterface_lib.embedded import \
            RRuntimeError as PackageNotInstalledError
    except ImportError:
        # Backward compat for rpy2 version < 3
        from rpy2.rinterface import RRuntimeError as PackageNotInstalledError

# Hide the R warnings
rpy2.robjects.r['options'](warn=-1)

# Set the R_HOME directory to the one of the R RHOME ouput
os.environ['R_HOME'] = rpy2.situation.r_home_from_subprocess()


def import_rpackages(*packages):
    """Helper to import R packages in the import_ctx"""

    base = rpackages.importr('base')
    R_PATH = base._libPaths()  # noqa: F841
    R_HOME = os.environ['R_HOME']  # noqa: F841
    os.environ["LD_LIBRARY_PATH"] = \
        rpy2.situation.r_ld_library_path_from_subprocess(R_HOME)
    for path in R_PATH:
        os.environ['LD_LIBRARY_PATH'] = path + ':' + \
             os.environ['LD_LIBRARY_PATH']
    LD_PATH = os.environ['LD_LIBRARY_PATH']  # noqa: F841
    TT = os.listdir(path)
    for t in TT:
        print(t)
    ISOK = os.path.isfile(f'{path}/glmnet/libs/glmnet.so')  # noqa: F841
    for pkg in packages:
        try:
            rpackages.importr(pkg)
        except PackageNotInstalledError:
            raise ImportError(f"R package '{pkg}' is not installed")


def import_func_from_r_file(filename):
    import rpy2.robjects as robjects
    r_source = robjects.r['source']
    r_source(filename)
