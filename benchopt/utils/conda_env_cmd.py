import os
import sys
import warnings
from pathlib import Path

import benchopt

from .shell_cmd import _run_shell
from .shell_cmd import _run_shell_in_conda_env
from .misc import get_benchopt_requirement, NamedTemporaryFile

from ..config import DEBUG
from ..config import get_setting

SHELL = get_setting('shell')
CONDA_CMD = get_setting('conda_cmd')

# On windows, calling conda without call exit the cmd script:
# https://github.com/conda/conda/issues/12418
if sys.platform == 'win32' and not CONDA_CMD.lower().startswith('call'):
    CONDA_CMD = f"CALL {CONDA_CMD}"


# Yaml config file for benchopt env.
BENCHOPT_ENV = """
channels:
  - conda-forge
  - nodefaults
dependencies:
  - python=3.10
  - numpy
  - cython
  - compilers
  - pip
  - pip:
    - {benchopt_requirement}
"""

EMPTY_ENV = """
channels:
  - conda-forge
  - nodefaults
dependencies:
  - python=3.10
"""


def create_conda_env(
        env_name, recreate=False, pytest=False, empty=False, quiet=False):
    """Create a conda env with name env_name and install basic utilities.


    Parameters
    ----------
    env_name : str
        The name of the conda env that will be created.
    recreate : bool (default: False)
        It the conda env exists and recreate is set to True, it will be
        overwritten with the new env. If it is False, the env will be untouched
    pytest : bool (default: False)
        If set to True, also install pytest in the newly created env.
    empty : bool (default: False)
        If set to True, simply create an empty env. This is mainly for testing
        purposes.
    quiet : bool (default: False)
        If True, silences the output of conda commands.
    """

    # Get a list of all conda envs
    _, existing_conda_envs = list_conda_envs()

    if env_name in existing_conda_envs and not recreate:
        print(
            f"Conda env {env_name} already exists. Checking setup ... ",
            end='', flush=True
        )
        env_version, editable_install = get_benchopt_version_in_env(env_name)
        if env_version is None:
            print()
            raise RuntimeError(
                f"`benchopt` is not installed in existing env '{env_name}'. "
                "This can lead to unexpected behavior. You can correct this "
                "by either using the --recreate option or installing benchopt "
                f"in conda env {env_name}."
            )
        if benchopt.__version__ != env_version and not editable_install:
            print()
            warnings.warn(
                f"The local version of benchopt ({benchopt.__version__}) and "
                f"the one in conda env ({env_version}) are different. "
                "This can lead to unexpected behavior. You can correct this "
                "by either using the --recreate option or fixing the version "
                f"of benchopt in conda env {env_name}."
            )
        print("done")
        return

    force = " --force" if recreate else ""

    benchopt_requirement, benchopt_editable = get_benchopt_requirement(pytest)

    benchopt_env = BENCHOPT_ENV.format(
        benchopt_requirement=benchopt_requirement
    )

    if empty:
        benchopt_env = EMPTY_ENV

    print(f"Creating conda env '{env_name}':... ", end='', flush=True)
    if DEBUG:
        print(f"\nconda env config:\n{'-' * 40}{benchopt_env}{'-' * 40}")
    env_yaml = NamedTemporaryFile(
        mode="w+", prefix='conda_env_', suffix='.yml'
    )
    env_yaml.write(f"name: {env_name}{benchopt_env}")
    env_yaml.flush()

    try:
        if not quiet:
            print()
        _run_shell(
            f"{CONDA_CMD} env create -yn{force} {env_name} -f {env_yaml.name}",
            capture_stdout=quiet, raise_on_error=True
        )
        # the channels priorities cannot be set through the yaml file,
        # we need to do it at the env creation
        # see https://stackoverflow.com/questions/70098418/
        _run_shell_in_conda_env(
            f"{CONDA_CMD} config --env --prepend channels nodefaults " +
            "--prepend channels conda-forge", env_name,
            capture_stdout=quiet)
        if empty:
            return
        # Check that the correct version of benchopt is installed in the env
        env_version, env_editable = get_benchopt_version_in_env(env_name)
        error_msg = (
            f"Installed the wrong version of benchopt ({env_version}) in "
            f"conda env. This should be version: {benchopt.__version__}. There"
            " is something wrong the env creation mechanism. Please report "
            "this error to https://github.com/benchopt/benchopt"
        )
        assert ((benchopt_editable and env_editable)
                or env_version == benchopt.__version__), error_msg
    except RuntimeError:
        print("failed to create the environment.")
        raise
    else:
        if quiet:
            print("done")


def get_benchopt_version_in_env(env_name):
    """Check that the version of benchopt installed in env_name is the same
    as the one running.
    """
    check_benchopt, output = _run_shell_in_conda_env(
        "benchopt --version --check-editable",
        env_name=env_name, capture_stdout=True, return_output=True
    )

    if check_benchopt != 0:
        if DEBUG:
            print(output)
        return None, None
    output = [
        line for line in output.splitlines()
        if line.startswith('BENCHOPT_VERSION:')
    ][0]
    _, benchopt_version, is_editable = output.split(":")

    return benchopt_version, is_editable == 'True'


def delete_conda_env(env_name):
    """Delete a conda env with name env_name."""

    _run_shell(f"{CONDA_CMD} env remove -yn {env_name}",
               capture_stdout=True)


def get_env_file_from_requirements(packages):
    """Process the packages from requirements and create the install cmd.

    This detects the packages that need to be installed with pip and also
    the additional channels for conda packages.
    """
    # TODO: remove with benchopt 1.9
    # If ":" is present but not "::", warn that this is legacy syntax.
    has_legacy_colon = any(":" in pkg and "::" not in pkg for pkg in packages)
    if has_legacy_colon:
        warnings.warn(
            "The use of ':' to specify the channel of a dependency is "
            "deprecated. Please use '::' instead.", DeprecationWarning
        )
        packages = [pkg.replace(":", "::", 1) for pkg in packages]

    conda_packages = [pkg for pkg in packages if not pkg.startswith('pip::')]
    if conda_packages:
        channels = '\n  - '.join(sorted(set(
            pkg.rsplit('::', 1)[0]
            for pkg in conda_packages if '::' in pkg
        )))
        channels = f"channels:\n  - {channels}\n" if channels else ""
        conda_packages = '\n  - '.join(sorted(set(
            pkg.rsplit('::', 1)[-1] for pkg in conda_packages
        )))
        env = f"{channels}dependencies:\n  - {conda_packages}"
    else:
        env = "dependencies:"

    pip_packages = '\n    - '.join(sorted(set(
        pkg.replace("pip::", "") for pkg in packages if pkg.startswith('pip::')
    )))
    if pip_packages:
        env += f"\n  - pip\n  - pip:\n    - {pip_packages}"

    return env


def install_in_conda_env(*packages, env_name=None, force=False, quiet=False):
    """Install the packages with conda in the given environment"""
    if len(packages) == 0:
        return

    env = get_env_file_from_requirements(packages)
    if DEBUG:
        print(f"\ninstalling env packages:\n{'-' * 40}{env}{'-' * 40}")

    # If installing in the current env, get its name.
    if env_name is None:
        env_name, _ = list_conda_envs()

    with NamedTemporaryFile(mode='w+', prefix='env_', suffix='.yml') as f:
        f.write(env)
        f.flush()
        cmd = (
            f"{CONDA_CMD} env update -n {env_name} -f {f.name}"
            f"{' -q' if quiet else ''}"
        )

        error_msg = (
            f"Failed to conda install packages {packages}\nError:{{output}}"
        )
        _run_shell_in_conda_env(
            cmd, env_name=env_name, raise_on_error=error_msg,
            capture_stdout=quiet
        )


def shell_install_in_conda_env(script, env_name=None, quiet=False):
    """Run a shell install script in the given environment"""

    cmd = f"{SHELL} {script} $CONDA_PREFIX"
    _run_shell_in_conda_env(cmd, env_name=env_name, capture_stdout=quiet,
                            raise_on_error=f"Failed to run script {script}\n"
                            "Error: {output}")


def list_conda_envs():
    """List all existing conda envs.

    Returns
    -------
    conda_envs : list of tuple (env_name, is_active)
        List of all conda envs in the system and whether they are the current
        env or not.
    """
    try:
        from conda.base.context import context
    except ImportError:
        context = get_conda_context()
        if context is None:
            # Not in an activated conda env, returns an empty list.
            return None, []

    def get_env_name(prefix):

        prefix = Path(prefix)
        is_active = prefix == Path(context.active_prefix)
        if prefix == Path(context.root_prefix):
            name = 'base'
        elif any(Path(envs_dir) == prefix.parent
                 for envs_dir in context.envs_dirs):
            name = prefix.name
        else:
            name = ''
        return name, is_active

    conda_prefixes = [context.root_prefix]
    for env_dir in context.envs_dirs:
        env_dir = Path(env_dir)
        if not env_dir.is_dir():
            continue
        for p in env_dir.glob('*'):
            if p.is_dir():
                conda_prefixes.append(p)

    all_envs = [get_env_name(prefix) for prefix in conda_prefixes]
    active_envs = [e[0] for e in all_envs if e[1]]
    all_envs = [e[0] for e in all_envs]

    if len(active_envs) == 0:
        return None, all_envs

    assert len(active_envs) == 1, "Multiple activated conda env?!."

    return active_envs[0], all_envs


def get_conda_context():
    import json
    from collections import namedtuple
    Context = namedtuple(
        'Context', ['active_prefix', 'root_prefix', 'envs_dirs']
    )

    exit_code, payload = _run_shell_in_conda_env(
        "conda config --show envs_dirs root_prefix --json", return_output=True
    )

    active_prefix = os.environ.get('CONDA_PREFIX', None)
    if exit_code != 0 or active_prefix is None:
        return None
    info = json.loads(payload)
    info['active_prefix'] = os.path.normpath(active_prefix)
    info['root_prefix'] = os.path.normpath(info['root_prefix'])
    info['envs_dirs'] = [os.path.normpath(env_dir) for env_dir
                         in info['envs_dirs']]
    return Context(**info)
