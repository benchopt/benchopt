import os
import tempfile
import subprocess
from pip._internal.commands.freeze import freeze

from ..config import get_global_setting
from ..config import DEBUG, ALLOW_INSTALL


SHELL = get_global_setting('shell')


# Shell commands for installing and checking the solvers
CONDA_INSTALL_CMD = "conda install -y {packages}"
PIP_INSTALL_CMD = "pip install {packages}"
SHELL_INSTALL_CMD = f"{SHELL} {{install_script}} $CONDA_PREFIX"

# Shell cmd to test if a cmd exists
CHECK_SHELL_CMD_EXISTS = "type $'{cmd_name}'"


# Find out how benchopt where installed so we can install the same version even
# if it was installed in develop mode. This requires pip version >= 20.1
BENCHOPT_INSTALL = [pkg for pkg in freeze() if 'benchopt' in pkg][0]

# Yaml config file for benchopt env.
BENCHOPT_ENV = f"""
channels:
  - defaults
  - conda-forge
dependencies:
  - numpy
  - cython
  - compilers
  - pip
  - pip:
    - {BENCHOPT_INSTALL}
"""


def _run_shell(script, raise_on_error=None, capture_stdout=True):
    """Run a shell script and return its exit code.

    Parameters
    ----------
    script: str
        Script to run
    raise_on_error: str or callable or None
        If raise_on_error is a string, raise a RuntimeError with the given
        message if the command's exit code is non-zero.
        If raise_on_error is a callable, when script output is non 0, call
        the callable with output as an argument `raise_on_error(output)`.
        Else, just return the exit code.
    capture_stdout: bool
        If set to True, capture the stdout of the subprocess. Else, it is
        printed in the main process stdout.

    Returns
    -------
    exit_code: int
        Exit code of the script
    """
    # Use a TemporaryFile to make sure this file is cleaned up at
    # the end of this function.
    tmp = tempfile.NamedTemporaryFile(mode="w+")
    fast_failure_script = f"set -e\n{script}"
    tmp.write(fast_failure_script)
    tmp.flush()

    if DEBUG:
        print(fast_failure_script)

    if raise_on_error is True:
        raise_on_error = "{output}"

    if capture_stdout:
        exit_code, output = subprocess.getstatusoutput([f"{SHELL} {tmp.name}"])
    else:
        exit_code = os.system(f"{SHELL} {tmp.name}")
        output = ""
    if raise_on_error is not None and exit_code != 0:
        if isinstance(raise_on_error, str):
            raise RuntimeError(raise_on_error.format(output=output))
        elif callable(raise_on_error):
            raise_on_error(output)
        elif raise_on_error is False:
            pass
        else:
            raise ValueError(
                "Bad value for `raise_on_error`. Should be a str, a callable, "
                f"a bool or None. Got {raise_on_error}."
            )
    return exit_code


def _run_shell_in_conda_env(script, env_name=None, raise_on_error=None,
                            capture_stdout=True):
    """Run a script in a given conda env

    Parameters
    ----------
    script: str
        Script to run
    env_name: str
        Name of the environment to run the script in.
    raise_on_error: str or None
        If raise_on_error is not None, raise a RuntimeError with the given
        message if the command's exit code is non-zero.
        Else, just return the exit code.
    capture_stdout: bool
        If set to True, capture the stdout of the subprocess. Else, it is
        printed in the main process stdout.

    Returns
    -------
    exit_code: int
        Exit code of the script
    """
    if env_name is not None:
        # first line to use conda activate in bash script
        # see https://github.com/conda/conda/issues/7980
        script = (f'eval "$(conda shell.bash hook)"\n'
                  f'conda activate {env_name}\n'
                  f'{script}')

    return _run_shell(script, raise_on_error=raise_on_error,
                      capture_stdout=capture_stdout)


def create_conda_env(env_name, recreate=False, with_pytest=False):
    """Create a conda env with name env_name and install basic utilities"""

    if env_exists(env_name) and not recreate:
        return

    force = "--force" if recreate else ""

    benchopt_env = BENCHOPT_ENV
    if with_pytest:
        # Add pytest as a dependency of the env
        benchopt_env = benchopt_env.replace(
            '- compilers', '- compilers\n  - pytest'
        )

    print(f"Creating conda env {env_name}:...", end='', flush=True)
    env_yaml = tempfile.NamedTemporaryFile(mode="w+", suffix='.yml')
    env_yaml.write(f"name: {env_name}{benchopt_env}")
    env_yaml.flush()
    try:
        _run_shell(
            f"conda env create {force} -n {env_name} -f {env_yaml.name}",
            capture_stdout=True, raise_on_error=True
        )
        _run_shell_in_conda_env(
            "conda config --env --add channels conda-forge",
            env_name=env_name, capture_stdout=True, raise_on_error=True
        )
    except RuntimeError:
        print(" failed to create the environment.")
        raise
    else:
        print(" done")


def env_exists(env_name):
    """Returns True if a given environment exists in the system."""
    try:
        _run_shell_in_conda_env(
            'which python',
            env_name=env_name, capture_stdout=True, raise_on_error=True
        )
        return True
    except RuntimeError:
        return False


def delete_conda_env(env_name):
    """Delete a conda env with name env_name."""

    _run_shell(f"conda env remove -n {env_name}",
               capture_stdout=True)


def install_in_conda_env(*packages, env_name=None, force=False):
    """Install the packages with conda in the given environment"""
    if env_name is None and not ALLOW_INSTALL:
        raise ValueError("Trying to install solver not in a conda env "
                         "managed by benchopt. To allow this, "
                         "set BENCHO_ALLOW_INSTALL=True.")

    pip_packages = [pkg[4:] for pkg in packages if pkg.startswith('pip:')]
    conda_packages = [pkg for pkg in packages if not pkg.startswith('pip:')]

    error_msg = ("Failed to conda install packages "
                 f"{packages if len(packages) > 1 else packages[0]}\n"
                 "Error:{output}")
    if conda_packages:
        cmd = CONDA_INSTALL_CMD.format(packages=' '.join(conda_packages))
        if force:
            cmd += ' --force-reinstall'
        _run_shell_in_conda_env(cmd, env_name=env_name,
                                raise_on_error=error_msg)
    if pip_packages:
        cmd = PIP_INSTALL_CMD.format(packages=' '.join(pip_packages))
        if force:
            cmd += ' --force-reinstall'
        _run_shell_in_conda_env(cmd, env_name=env_name,
                                raise_on_error=error_msg)


def shell_install_in_conda_env(script, env_name=None):
    """Run a shell install script in the given environment"""
    if env_name is None and not ALLOW_INSTALL:
        raise ValueError("Trying to install solver not in a conda env. "
                         "To allow this, set BENCHO_ALLOW_INSTALL=True.")

    cmd = SHELL_INSTALL_CMD.format(install_script=script)
    _run_shell_in_conda_env(cmd, env_name=env_name,
                            raise_on_error=f"Failed to run script {script}\n"
                            "Error: {output}")
