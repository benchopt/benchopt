

def get_benchopt_requirement():
    """Specification for pip requirement to install benchopt in conda env.

    Find out how benchopt where installed so we can install the same version
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

    # If benchopt is installed in editable mode, get the module path to install
    # it directly from the folder. Else, install it correctly even if it is
    # installed with an url.
    assert dist is not None, (
        'benchopt is not installed in the current environment?'
    )
    req = FrozenRequirement.from_dist(dist)
    if req.editable:
        return f'-e {dist.location}', True

    return str(req), False
