"""``uv`` backend for ``benchopt install``.

Uses `uv <https://docs.astral.sh/uv/>`_ to manage PyPI-only virtual
environments. Faster than conda for the pure-Python case; cannot
handle conda-channel dependencies (``chan::pkg``) — such requirements
trigger skip-with-warn through :meth:`can_install`.

Env locations are stored under ``~/.local/share/benchopt/envs/<name>``
by default (override with the ``uv_envs_dir`` setting).
"""
import os
import shutil
import sys
import warnings
from pathlib import Path

import benchopt

from ..shell_cmd import _run_shell
from ..misc import get_benchopt_requirement
from ...config import DEBUG
from .base import EnvBackend
from .python_version import (
    DEFAULT_PYTHON_VERSION,
    _python_version_satisfies,
    get_benchmark_python_version,
)


IS_WIN = sys.platform == 'win32'


def _default_uv_envs_dir():
    """Where bare-name uv venvs live by default."""
    xdg = os.environ.get('XDG_DATA_HOME')
    if xdg:
        return Path(xdg) / 'benchopt' / 'envs'
    return Path.home() / '.local' / 'share' / 'benchopt' / 'envs'


def _strip_pip_prefix(requirement):
    """Return the PyPI-installable form of a requirement string.

    ``pip::foo`` → ``foo``; bare ``foo`` → ``foo``. Channel-prefixed
    entries should be filtered out by :meth:`UvBackend.can_install`
    upstream and never reach this point.
    """
    if requirement.startswith('pip::'):
        return requirement[len('pip::'):]
    return requirement


def _uv_cmd():
    """Path to the ``uv`` executable (raise if missing)."""
    exe = shutil.which('uv')
    if exe is None:
        raise RuntimeError(
            "uv backend requested but the 'uv' binary is not on PATH. "
            "Install it from https://docs.astral.sh/uv/getting-started/ "
            "(e.g. `pip install uv`) and re-run."
        )
    return exe


def _venv_python(env_path):
    """Path to the venv's python interpreter."""
    if IS_WIN:
        return str(Path(env_path) / 'Scripts' / 'python.exe')
    return str(Path(env_path) / 'bin' / 'python')


def _activate_prefix(env_path):
    """Shell snippet that activates the venv at ``env_path``."""
    if IS_WIN:
        return f'CALL "{env_path}\\Scripts\\activate.bat"\n'
    return f'source "{env_path}/bin/activate"\n'


class UvBackend(EnvBackend):
    """:class:`EnvBackend` implementation backed by ``uv``.

    See module docstring for design notes.
    """

    name = "uv"

    # ------------------------------------------------------------------
    # Env path resolution
    # ------------------------------------------------------------------
    @staticmethod
    def envs_dir():
        try:
            from ...config import get_setting
            value = get_setting('uv_envs_dir')
            if value:
                return Path(value).expanduser()
        except (KeyError, AssertionError):
            pass
        return _default_uv_envs_dir()

    @classmethod
    def env_path(cls, env_name):
        """Resolve ``env_name`` to a filesystem path.

        Bare names live under :meth:`envs_dir`. Anything containing a
        path separator or starting with ``~`` / ``.`` is treated as a
        path and used as-is (after expanduser).
        """
        if env_name is None:
            active = os.environ.get('VIRTUAL_ENV')
            if active:
                return Path(active)
            raise RuntimeError(
                "No env_name given and no VIRTUAL_ENV is active."
            )
        s = str(env_name)
        if (os.sep in s or '/' in s or s.startswith('~')
                or s.startswith('.')):
            return Path(s).expanduser()
        return cls.envs_dir() / s

    # ------------------------------------------------------------------
    # Discovery / state
    # ------------------------------------------------------------------
    def list_envs(self):
        envs_dir = self.envs_dir()
        all_envs = []
        if envs_dir.is_dir():
            all_envs = sorted(
                p.name for p in envs_dir.iterdir() if p.is_dir()
            )

        active = None
        venv = os.environ.get('VIRTUAL_ENV')
        if venv:
            venv_path = Path(venv)
            if venv_path.parent == envs_dir:
                active = venv_path.name
            else:
                # Active venv is outside our envs dir — still report
                # it by its absolute path so callers can disambiguate.
                active = str(venv_path)
        return active, all_envs

    def get_env_info(self, env_name):
        env_path = self.env_path(env_name)
        python = _venv_python(env_path)
        if not Path(python).exists():
            return dict(version=None, is_editable=False,
                        python_version=None, pytest_version=None)
        exit_code, output = _run_shell(
            f'"{python}" -m benchopt --check-env',
            capture_stdout=True, return_output=True,
        )
        if exit_code != 0:
            if DEBUG:
                print(output)
            return dict(version=None, is_editable=False,
                        python_version=None, pytest_version=None)
        import json
        return json.loads(output.strip().splitlines()[-1])

    def is_active_env_compatible(self):
        # If a conda env is active, prefer that to a uv venv — but only
        # the explicit --backend selection actually pins the choice.
        return bool(os.environ.get('VIRTUAL_ENV'))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def create_env(self, env_name, *, benchmark=None, recreate=False,
                   pytest=False, empty=False, quiet=False):
        env_path = self.env_path(env_name)
        python_version = get_benchmark_python_version(benchmark)

        if env_path.exists() and not recreate:
            print(
                f"uv env {env_name} already exists. Checking setup ... ",
                end='', flush=True
            )
            info = self.get_env_info(env_name)
            if info['version'] is None:
                print()
                raise RuntimeError(
                    f"`benchopt` is not installed in existing env "
                    f"'{env_name}'. This can lead to unexpected behavior. "
                    "Use --recreate or install benchopt manually."
                )
            if (benchopt.__version__ != info['version']
                    and not info['is_editable']):
                print()
                warnings.warn(
                    f"The local version of benchopt ({benchopt.__version__})"
                    f" and the one in uv env ({info['version']}) differ. "
                    "Use --recreate or fix the version in the env."
                )
            if pytest and info.get('pytest_version') is None:
                raise ModuleNotFoundError(
                    f"pytest is not installed in uv env {env_name}.\n"
                    f"Run `uv pip install --python {_venv_python(env_path)} "
                    "pytest` to test the benchmark."
                )
            if benchmark is not None and info['python_version']:
                env_py = info['python_version'].strip().split()[-1]
                if not _python_version_satisfies(env_py, python_version):
                    print()
                    warnings.warn(
                        f"The python version in uv env ({env_py}) differs "
                        f"from the one required by the benchmark "
                        f"({python_version}). Use --recreate."
                    )
            print("done")
            return False

        if recreate and env_path.exists():
            # Defensive guards: never delete the active venv, never go
            # outside our envs_dir for a bare name.
            assert str(env_name) != "base", "Cannot recreate base"
            if str(env_path) == os.environ.get('VIRTUAL_ENV'):
                raise RuntimeError(
                    "Refusing to recreate the currently activated venv."
                )
            print(
                f"Recreate is used, removing uv env '{env_name}'... ",
                end='', flush=True
            )
            shutil.rmtree(env_path)
            print("done")

        env_path.parent.mkdir(parents=True, exist_ok=True)
        uv = _uv_cmd()

        print(f"Creating uv env '{env_name}':... ", end='', flush=True)
        if DEBUG:
            print(f"\nuv env config:\n{'-' * 60}\npython={python_version}"
                  f"\nenv_path={env_path}\n{'-' * 60}")

        # Strip any leading specifier characters so uv accepts the value
        # both for plain versions (3.12) and ranges (>=3.12).
        py_arg = str(python_version) or DEFAULT_PYTHON_VERSION
        try:
            # ``--seed`` installs pip in the venv. benchopt's
            # ``get_benchopt_requirement`` imports pip internals to detect
            # editable installs, so we need it available inside the env.
            _run_shell(
                f'"{uv}" venv --seed --python "{py_arg}" "{env_path}"',
                capture_stdout=quiet, raise_on_error=True,
            )
            if empty:
                if quiet:
                    print("done")
                return True

            benchopt_req, _ = get_benchopt_requirement(pytest)
            benchopt_req = benchopt_req.replace("\\", "/")
            _run_shell(
                f'"{uv}" pip install --python "{_venv_python(env_path)}" '
                f'{benchopt_req}',
                capture_stdout=quiet, raise_on_error=True,
            )
        except RuntimeError:
            print("failed to create the environment.")
            raise

        if quiet:
            print("done")
        return True

    def delete_env(self, env_name):
        env_path = self.env_path(env_name)
        if env_path.exists():
            shutil.rmtree(env_path)

    # ------------------------------------------------------------------
    # Package install
    # ------------------------------------------------------------------
    def can_install(self, requirement):
        """Return False for any channel-prefixed requirement except pip::.

        ``pkg``, ``pip::pkg`` and ``pkg=1.2`` are all installable via PyPI.
        ``conda-forge::pkg``, ``pytorch::pytorch`` etc. cannot be expressed
        and trigger skip-with-warn upstream.
        """
        # Tolerate the legacy single-colon syntax that ``get_env_file_
        # from_requirements`` warns about elsewhere.
        normalized = requirement
        if ":" in normalized and "::" not in normalized:
            normalized = normalized.replace(":", "::", 1)
        if normalized.startswith("pip::"):
            return True
        return "::" not in normalized

    def install_packages(self, *packages, env_name=None, quiet=False):
        if not packages:
            return
        env_path = self.env_path(env_name)
        if not Path(_venv_python(env_path)).exists():
            raise RuntimeError(
                f"uv env at '{env_path}' is not initialized; "
                "create it first with --env / --env-name and --recreate."
            )
        uv = _uv_cmd()
        pkgs = " ".join(
            f'"{_strip_pip_prefix(p)}"' for p in packages
        )
        cmd = (
            f'"{uv}" pip install --python "{_venv_python(env_path)}" {pkgs}'
            f'{" -q" if quiet else ""}'
        )
        error_msg = (
            f"Failed to uv pip install packages {packages}\nError:{{output}}"
        )
        _run_shell(cmd, capture_stdout=quiet, raise_on_error=error_msg)

    def install_shell_script(self, script, *, env_name=None, quiet=False):
        env_path = self.env_path(env_name)
        cmd = (
            _activate_prefix(env_path)
            + f'bash "{script}" "{env_path}"\n'
        )
        _run_shell(
            cmd, capture_stdout=quiet,
            raise_on_error=f"Failed to run script {script}\nError: {{output}}",
        )

    # ------------------------------------------------------------------
    # Run inside env
    # ------------------------------------------------------------------
    def run_in_env(self, script, *, env_name=None, raise_on_error=None,
                   capture_stdout=True, return_output=False):
        env_path = self.env_path(env_name)
        wrapped = _activate_prefix(env_path) + script
        return _run_shell(
            wrapped, raise_on_error=raise_on_error,
            capture_stdout=capture_stdout, return_output=return_output,
        )


__all__ = ["UvBackend"]
