"""Deprecated module — kept as a back-compat shim.

All conda env-management helpers have moved to
:mod:`benchopt.utils.env_management.conda`. This module re-exports them
so that ``from benchopt.utils.conda_env_cmd import X`` keeps working.
"""
from .env_management.conda import (  # noqa: F401
    BENCHOPT_ENV,
    EMPTY_ENV,
    CONDA_CMD,
    SHELL,
    DEFAULT_PYTHON_VERSION,
    _python_version_conda_spec,
    _python_version_satisfies,
    _run_shell_in_conda_env,
    get_benchmark_python_version,
    create_conda_env,
    delete_conda_env,
    get_env_info,
    get_env_file_from_requirements,
    install_in_conda_env,
    shell_install_in_conda_env,
    list_conda_envs,
    get_conda_context,
    CondaBackend,
)
