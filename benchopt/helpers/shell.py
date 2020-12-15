
from benchopt.utils.shell_cmd import _run_shell_in_conda_env


# Shell cmd to test if a cmd exists
CHECK_SHELL_CMD_EXISTS = "type $'{cmd_name}'"


def import_shell_cmd(cmd_name, env_name=None):
    """Check that a cmd is available in an environment.

    Parameters
    ----------
    cmd_name : str
        Name of the cmd that should be installed. This function checks that
        this cmd is available on the path of the environment.
    env_name : str or None
        Name of the conda environment to check. If it is None, check in the
        current environment.

    Return
    """
    def raise_import_error(output):
        raise ImportError(
            f'Could not find {cmd_name} on the path of conda env {env_name}\n'
            f'{output}'
        )
    _run_shell_in_conda_env(
        CHECK_SHELL_CMD_EXISTS.format(cmd_name=cmd_name),
        env_name=env_name, raise_on_error=raise_import_error
    )

    def run_shell_cmd(*args):
        cmd_args = " ".join(args)
        _run_shell_in_conda_env(
            f"{cmd_name} {cmd_args}", env_name=env_name, raise_on_error=True
        )

    return run_shell_cmd
