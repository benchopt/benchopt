import rpy2
import rpy2.robjects.packages as rpackages
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


def import_rpackages(*packages):
    """Helper to import R packages in the import_ctx"""
    for pkg in packages:
        try:
            rpackages.importr(pkg)
        except PackageNotInstalledError:
            raise ImportError(f"R package '{pkg}' is not installed")


def import_func_from_r_file(filename):
    import rpy2.robjects as robjects
    r_source = robjects.r['source']
    r_source(filename)
