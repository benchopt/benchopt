import sys
from pathlib import Path
import tempfile

# Drop when dropping support for 3.8
if sys.version_info < (3, 9):
    def is_relative_to(p1, p2):
        try:
            p1.relative_to(p2)
            return True
        except ValueError:
            return False
else:
    def is_relative_to(p1, p2):
        return p1.is_relative_to(p2)


def get_benchopt_requirement(pytest=False):
    """Specification for pip requirement to install benchopt in conda env.

    Find out how benchopt was installed so we can install the same version
    even if it was installed in develop mode. This requires pip version >= 20.1

    Parameters
    ----------
    pytest : bool (default: False)
        If set to True, add [test] to extra requirements.

    Returns
    -------
    pip_requirement : str
        String to pass to pip to instal benchopt in another environment.
    is_editable : bool
        Whether the current installation is in development mode or not.
    """
    # Ignore distutils replacement warning when importing pip package. It is
    # not clear why this started to trigger such warning in #265
    # XXX - Investigate this warning and fix it.
    import warnings
    warnings.filterwarnings(
        "ignore", message="Setuptools is replacing distutils.",
        category=UserWarning
    )
    from pip._internal.metadata import get_default_environment
    from pip._internal.operations.freeze import FrozenRequirement

    dist = get_default_environment().get_distribution('benchopt')
    req = FrozenRequirement.from_dist(dist)

    # If benchopt is installed in editable mode, get the module path to install
    # it directly from the folder. Else, install it correctly even if it is
    # installed with an url.
    assert dist is not None, (
        'benchopt is not installed in the current environment?'
    )

    extra = '[test]' if pytest else ''

    # If pip version >= 21.3, use editable detection from dist.
    if hasattr(dist, 'editable_project_location'):
        if dist.editable:
            return f'-e {dist.editable_project_location}{extra}', True
        # handle the case where benchopt is local. In this case, use an
        # editable install, as this is not possible to distinguish between
        # the two behavior.
        if is_relative_to(Path(dist.location), Path().resolve()):
            return f'-e {dist.location}{extra}', True

    # Else, resort to req.editable and dist.location, as dist.editable
    # and dist.editable_project_location were not implemented before
    else:
        if req.editable:
            return f'-e {dist.location}{extra}', True
    req = str(req).strip('\n')

    if pytest:
        # Add pytest as a dependency of the env
        if "/" in req:
            # If it is a local path or an URL, we need to add the egg
            req = f"{req}#egg=benchopt[test]"
        else:
            # else simply add the test extra
            req = req.replace(
                "benchopt", "benchopt[test]"
            )

    return req, False


def NamedTemporaryFile(dir=None, mode='w+b', prefix=None,
                       suffix=None):
    """
    Returns a NamedTemporaryFile object, ensuring compatibility across Unix
    and Windows systems.

    On Unix systems, this function returns a standard NamedTemporaryFile,
    which is deleted upon closing.

    On Windows systems, it returns a NamedTemporaryFile with
    delete_on_close=False to handle the differences in how Windows treats
    temporary files. This compatibility on Windows requires python>=3.12.

    For more information, refer to the official Python documentation:
    https://docs.python.org/3/library/tempfile.html#tempfile.NamedTemporaryFile

    Returns:
        tempfile.NamedTemporaryFile: A named temporary file object.
    """
    if sys.platform != 'win32':
        return tempfile.NamedTemporaryFile(dir=dir, mode=mode, prefix=prefix,
                                           suffix=suffix)

    else:
        required_version = (3, 12)
        current_version = sys.version_info

        if current_version < required_version:
            raise EnvironmentError(
                f"Your current Python version is {current_version.major}."
                f"{current_version.minor}. Please upgrade to Python 3.12 or"
                "higher for benchopt to work correctly on Windows."
            )
        return tempfile.NamedTemporaryFile(dir=dir, mode=mode, prefix=prefix,
                                           suffix=suffix, delete=True,
                                           delete_on_close=False)
