import os
import tempfile
import subprocess

from ..config import DEBUG
from ..config import get_setting


SHELL = get_setting('shell')
CONDA_CMD = get_setting('conda_cmd')


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
