import os

# Make sure that R_HOME is loaded from the current interpreter to avoid
# using the parent interpreter R_HOME in the sub-interpreter.
if os.environ.get('R_HOME', None) is not None:
    del os.environ['R_HOME']

try:
    import rpy2  # noqa: F401
except ImportError:
    raise ImportError(
        "rpy2 is not installed. Please make sure the solver requirements are "
        "installed. If the requirements are missing, add "
        "`requirements = ['r-base', 'rpy2']` to your solver."
    )


def setup_rpy2():
    import rpy2.situation
    import rpy2.robjects

    # Set the R_HOME directory to the one of the R RHOME ouput
    os.environ['R_HOME'] = rpy2.situation.r_home_from_subprocess()

    # Hide the R warnings
    rpy2.robjects.r['options'](warn=-1)


def get_package_not_installed_error():
    try:
        from rpy2.robjects.packages import PackageNotInstalledError
    except ImportError:
        # Backward compat for rpy2 version < 3.3
        try:
            from rpy2.rinterface_lib.embedded import RRuntimeError as \
                PackageNotInstalledError
        except ImportError:
            # Backward compat for rpy2 version < 3
            from rpy2.rinterface import RRuntimeError as \
                PackageNotInstalledError
    return PackageNotInstalledError


def import_rpackages(*packages):
    """Helper to import R packages in the import_ctx"""
    setup_rpy2()
    PackageNotInstalledError = get_package_not_installed_error()
    import rpy2.robjects.packages as rpackages
    for pkg in packages:
        try:
            rpackages.importr(pkg)
        except PackageNotInstalledError:
            raise ImportError(f"R package '{pkg}' is not installed")


def import_func_from_r_file(filename):
    setup_rpy2()
    import rpy2.robjects as robjects
    r_source = robjects.r['source']
    r_source(filename)
    return robjects


def converter_ctx():
    from rpy2.robjects import numpy2ri
    from rpy2.robjects import default_converter
    return (default_converter + numpy2ri.converter).context()
