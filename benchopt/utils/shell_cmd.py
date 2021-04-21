import os
import tempfile
import warnings
import subprocess

import benchopt

from ..config import get_setting
from ..config import DEBUG, ALLOW_INSTALL

from .misc import list_conda_envs
from .misc import get_benchopt_requirement_line


SHELL = get_setting('shell')
CONDA_CMD = get_setting('conda_cmd')

# Yaml config file for benchopt env.
BENCHOPT_ENV = """
channels:
  - defaults
  - conda-forge
dependencies:
  - numpy
  - cython
  - compilers
  - pip
  - pip:
    - {benchopt_install}
"""
EMPTY_ENV = """
channels:
  - defaults
  - conda-forge
"""


def _run_shell(script, raise_on_error=None, capture_stdout=True,
               return_output=False):
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
    return_output: bool
        If set to True, return the stdout of the subprocess. It needs to be
        used with capture_stdout=True.

    Returns
    -------
    exit_code: int
        Exit code of the script.
    output: str
        If return_output=True, return the output of the command as a str.
    """
    if return_output and not capture_stdout:
        raise ValueError(
            'return_output=True can only be used with capture_stdout=True'
        )

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
    if return_output:
        return exit_code, output
    return exit_code


def _run_shell_in_conda_env(script, env_name=None, raise_on_error=None,
                            capture_stdout=True, return_output=False):
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
    return_output: bool
        If set to True, return the stdout of the subprocess. It needs to be
        used with capture_stdout=True.

    Returns
    -------
    exit_code: int
        Exit code of the script.
    output: str
        If return_output=True, return the output of the command as a str.
    """
    if env_name is not None:
        # first line to use conda activate in bash script
        # see https://github.com/conda/conda/issues/7980
        script = (f'eval "$({CONDA_CMD} shell.bash hook)"\n'
                  f'{CONDA_CMD} activate {env_name}\n'
                  f'{script}')

    return _run_shell(
        script, raise_on_error=raise_on_error,
        capture_stdout=capture_stdout, return_output=return_output
    )


def create_conda_env(env_name, recreate=False, with_pytest=False, empty=False):
    """Create a conda env with name env_name and install basic utilities.


    Parameters
    ----------
    env_name : str
        The name of the conda env that will be created.
    recreate : bool (default: False)
        It the conda env exists and recreate is set to True, it will be
        overwritten with the new env. If it is False, the env will be untouched
    with_pytest : bool (default: False)
        If set to True, also install pytest in the newly created env.
    empty : bool (default: False)
        If set to True, simply create an empty env. This is mainly for testing
        purposes.
    """

    # Get a list of all conda envs
    _, existing_conda_envs = list_conda_envs()

    if env_name in existing_conda_envs and not recreate:
        benchopt_version = get_benchopt_version_in_env(env_name)
        if benchopt_version is None:
            raise RuntimeError(
                f"`benchopt` is not installed in existing env '{env_name}'. "
                "This can lead to unexpected behavior. You can correct this "
                "by either using the --recreate option or installing benchopt "
                f"in conda env {env_name}."
            )
        if benchopt.__version__ != benchopt_version:
            warnings.warn(
                f"The local version of benchopt ({benchopt.__version__}) and "
                f"the one in conda env ({benchopt_version}) are different. "
                "This can lead to unexpected behavior. You can correct this "
                "by either using the --recreate option or fixing the version "
                f"of benchopt in conda env {env_name}."
            )
        return

    force = "--force" if recreate else ""

    benchopt_env = BENCHOPT_ENV.format(
        benchopt_install=get_benchopt_requirement_line()
    )

    if with_pytest:
        # Add pytest as a dependency of the env
        benchopt_env = benchopt_env.replace(
            '- pip:', '- pytest\n  - pip:\n'
        )

    if empty:
        benchopt_env = EMPTY_ENV

    print(f"Creating conda env '{env_name}':...", end='', flush=True)
    if DEBUG:
        print(f"\nconda env config:\n{'-' * 40}{benchopt_env}{'-' * 40}")
    env_yaml = tempfile.NamedTemporaryFile(
        mode="w+", prefix='conda_env_', suffix='.yml'
    )
    env_yaml.write(f"name: {env_name}{benchopt_env}")
    env_yaml.flush()
    try:
        _run_shell(
            f"{CONDA_CMD} env create {force} -n {env_name} -f {env_yaml.name}",
            capture_stdout=True, raise_on_error=True
        )
        _run_shell_in_conda_env(
            f"{CONDA_CMD} config --env --add channels conda-forge",
            env_name=env_name, capture_stdout=True, raise_on_error=True
        )
        if empty:
            return
        # Check that the correct version of benchopt is installed in the env
        benchopt_version = get_benchopt_version_in_env(env_name)
        assert benchopt_version == benchopt.__version__, (
            f"Installed the wrong version of benchopt ({benchopt_version}) in "
            f"conda env. This should be version: {benchopt.__version__}. There"
            " is something wrong the env creation mechanism. Please report "
            "this error to https://github.com/benchopt/benchopt"
        )
    except RuntimeError:
        print(" failed to create the environment.")
        raise
    else:
        print(" done")


def get_benchopt_version_in_env(env_name):
    """Check that the version of benchopt installed in env_name is the same
    as the one running.
    """
    check_benchopt, benchopt_version = _run_shell_in_conda_env(
        "benchopt --version",
        env_name=env_name, capture_stdout=True, return_output=True
    )
    if check_benchopt != 0:
        return None
    return benchopt_version


def delete_conda_env(env_name):
    """Delete a conda env with name env_name."""

    _run_shell(f"{CONDA_CMD} env remove -n {env_name}",
               capture_stdout=True)


def install_in_conda_env(*packages, env_name=None, force=False):
    """Install the packages with conda in the given environment"""
    if env_name is None and not ALLOW_INSTALL:
        raise ValueError("Trying to install solver not in a conda env "
                         "managed by benchopt. To allow this, "
                         "set BENCHOPT_ALLOW_INSTALL=True.")

    pip_packages = [pkg[4:] for pkg in packages if pkg.startswith('pip:')]
    conda_packages = [pkg for pkg in packages if not pkg.startswith('pip:')]

    error_msg = ("Failed to conda install packages "
                 f"{packages if len(packages) > 1 else packages[0]}\n"
                 "Error:{output}")
    if conda_packages:
        packages = ' '.join(conda_packages)
        cmd = f"{CONDA_CMD} install -y {packages}"
        if force:
            cmd += ' --force-reinstall'
        _run_shell_in_conda_env(cmd, env_name=env_name,
                                raise_on_error=error_msg)
    if pip_packages:
        packages = ' '.join(pip_packages)
        cmd = f"pip install {packages}"
        if force:
            cmd += ' --force-reinstall'
        _run_shell_in_conda_env(cmd, env_name=env_name,
                                raise_on_error=error_msg)


def shell_install_in_conda_env(script, env_name=None):
    """Run a shell install script in the given environment"""
    if env_name is None and not ALLOW_INSTALL:
        raise ValueError("Trying to install solver not in a conda env. "
                         "To allow this, set BENCHOPT_ALLOW_INSTALL=True.")

    cmd = f"{SHELL} {script} $CONDA_PREFIX"
    _run_shell_in_conda_env(cmd, env_name=env_name,
                            raise_on_error=f"Failed to run script {script}\n"
                            "Error: {output}")
