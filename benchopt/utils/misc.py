import sys
from pathlib import Path

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


def get_benchopt_requirement():
    """Specification for pip requirement to install benchopt in conda env.

    Find out how benchopt was installed so we can install the same version
    even if it was installed in develop mode. This requires pip version >= 20.1

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

    # If pip version >= 21.3, use editable detection from dist.
    if hasattr(dist, 'editable_project_location'):
        if dist.editable:
            return f'-e {dist.editable_project_location}', True
        # handle the case where benchopt is local. In this case, use an
        # editable install, as this is not possible to distinguish between
        # the two behavior.
        if is_relative_to(Path(dist.location), Path().resolve()):
            return f'-e {dist.location}', True

    # Else, resort to req.editable and dist.location, as dist.editable
    # and dist.editable_project_location were not implemented before
    else:
        if req.editable:
            return f'-e {dist.location}', True
    return str(req).strip('\n'), False
