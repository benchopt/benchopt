

def get_benchopt_requirement_line():
    """Specification for pip requirement to install benchopt in conda env.

    Find out how benchopt where installed so we can install the same version
    even if it was installed in develop mode. This requires pip version >= 20.1
    """
    from pip._internal.operations.freeze import FrozenRequirement
    from pip._internal.utils.misc import get_installed_distributions

    # If benchopt is installed in editable mode, get the module path to install
    # it directly from the folder. Else, install it correctly even if it is
    # installed with an url.
    dist = [t for t in get_installed_distributions()
            if t.project_name == 'benchopt'][0]
    req = FrozenRequirement.from_dist(dist)
    if req.editable:
        return f'-e {dist.module_path}'

    return str(req)
