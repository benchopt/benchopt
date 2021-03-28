import os
import tempfile
import warnings
import subprocess

import benchopt
from ..config import get_setting
from ..config import DEBUG, ALLOW_INSTALL
from .misc import get_benchopt_requirement_line


SHELL = get_setting('shell')
CONDA_CMD = get_setting('conda_cmd')

# Yaml config file for benchopt env.
BENCHOPT_ENV = """
channels:
  - defaults
  - conda-forge
  - conda-forge/label/cf202003
dependencies:
  - numpy
  - cython
  - compilers
  - pip
  - pip:
    - {benchopt_install}
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

    # Make sure the script fail at first failure
    fast_failure_script = f"set -e\n{script}"

    # Use a TemporaryFile to make sure this file is cleaned up at
    # the end of this function.
    tmp = tempfile.NamedTemporaryFile(mode="w+")
    tmp.write(fast_failure_script)
    tmp.flush()

    if DEBUG:
        print("-" * 60 + f'\n{fast_failure_script}\n' + "-" * 60)

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
        # Add necessary calls to make the script run in conda env.
        script = (
            # Make sure R_HOME is never passed down to subprocesses in differnt
            # conda env as it might lead to trying to load packages from the
            # wrong distribution.
            '# Setup conda\nunset R_HOME\n'

            # Run hook to setup conda and activate the env.
            # first line to use conda activate in bash script
            # see https://github.com/conda/conda/issues/7980
            f'eval "$({CONDA_CMD} shell.bash hook)"\n'
            f'{CONDA_CMD} activate {env_name}\n\n'

            # Run the actual script
            '# Run script\n'
            f'{script}'
        )

    return _run_shell(
        script, raise_on_error=raise_on_error,
        capture_stdout=capture_stdout, return_output=return_output
    )


def create_conda_env(env_name, recreate=False, with_pytest=False):
    """Create a conda env with name env_name and install basic utilities"""

    if env_exists(env_name) and not recreate:
        benchopt_version = get_benchopt_version_in_env(env_name)
        if benchopt.__version__ != benchopt_version:
            warnings.warn(
                f"The local version of benchopt ({benchopt.__version__}) and "
                f"the one in conda env ({benchopt_version}) are different. "
                "This can lead to unexpected behavior. You can correct this "
                " by either using the --recreate option or fixing the version "
                f"of benchopt in conda env {env_name}"
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

    print(f"Creating conda env {env_name}:...", end='', flush=True)
    if DEBUG:
        print(f'\nconda env config:\n{benchopt_env}')
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
    _, benchopt_version = _run_shell_in_conda_env(
        "benchopt --version",
        env_name=env_name, capture_stdout=True, return_output=True
    )
    return benchopt_version


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
