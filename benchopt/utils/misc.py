from pathlib import Path


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


def list_conda_envs():
    """List all existing conda envs.

    Returns
    -------
    conda_envs : list of tuple (env_name, is_default)
        List of all conda envs in the system and whether they are the current
        env or not.
    """
    try:
        from conda.core.envs_manager import list_all_known_prefixes
        from conda.base.context import context
    except ImportError:
        # Not in an activated conda env, returns an empty list.
        return None, []

    def get_env_name(prefix):

        default = prefix == context.default_prefix
        prefix = Path(prefix)
        if prefix == Path(context.root_prefix):
            name = 'base'
        elif any(Path(envs_dir) == prefix.parent
                 for envs_dir in context.envs_dirs):
            name = prefix.name
        else:
            name = ''
        return name, default

    conda_prefixes = list_all_known_prefixes()
    all_envs = [get_env_name(prefix) for prefix in conda_prefixes]
    default_envs = [e[0] for e in all_envs if e[1]]
    all_envs = [e[0] for e in all_envs]

    if len(default_envs) == 0:
        return None, all_envs

    assert len(default_envs) == 1, "Multiple activated conda env?!."

    return default_envs[0], all_envs
