import subprocess

from ..config import DEBUG
from ..config import get_setting

from benchopt.utils.misc import NamedTemporaryFile


SHELL = get_setting('shell')

IS_FISH = 'fish' in f"{SHELL}"
IS_CMD = 'cmd' in f"{SHELL}"


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
    if IS_FISH:
        fast_failure_script = f"begin; {script}; or exit 1; end"
    elif IS_CMD:
        fast_failure_script = '\n'.join([
            f"{step}\nif %errorlevel% neq 0 exit %ERRORLEVEL%\n"
            if step.strip() else ""
            for step in script.split("\n")
        ])
        fast_failure_script = f"@echo off\n{fast_failure_script}"
    else:
        fast_failure_script = f"set -e\n{script}"

    # Use a TemporaryFile to make sure this file is cleaned up at
    # the end of this function.
    tmp = NamedTemporaryFile(
        mode="w+", suffix=".sh" if not IS_CMD else ".bat"
    )
    tmp.write(fast_failure_script)
    tmp.flush()

    if DEBUG:
        print("-" * 60 + f'\n{fast_failure_script}\n' + "-" * 60)

    if raise_on_error is True:
        raise_on_error = "{output}"

    command = f'{SHELL} "{tmp.name}"'

    if capture_stdout:
        exit_code, output = subprocess.getstatusoutput(command)
    else:
        exit_code = subprocess.run(command, shell=True, stdin=None).returncode
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
    """Deprecated back-compat shim.

    Use :func:`benchopt.utils.env_management.conda._run_shell_in_conda_env`
    or call ``get_backend().run_in_env(...)`` instead.
    """
    from .env_management.conda import (
        _run_shell_in_conda_env as _impl,
    )
    return _impl(
        script, env_name=env_name, raise_on_error=raise_on_error,
        capture_stdout=capture_stdout, return_output=return_output,
    )
