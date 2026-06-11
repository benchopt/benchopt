"""Env-management backend protocol and registry.

A backend abstracts the operations ``benchopt install`` performs on a
target environment: creating it, installing packages into it, and
running commands inside it. The default backend (``conda``) preserves
the legacy behavior; the ``uv`` and ``requirements`` backends provide
alternatives.
"""
import os
from abc import ABC, abstractmethod

from ...config import get_setting


# Filled by the per-backend modules at import time.
BACKENDS = {}

# Active backend for the current process. Resolved on demand by
# ``get_backend`` and reset by ``reset_active_backend`` (mostly for tests).
_active_backend_name = None


class EnvBackend(ABC):
    """Abstract base class for env-management backends.

    The CondaBackend implementation defines the reference semantics and
    is the default. Other backends override the relevant methods.

    Subclasses are auto-registered in ``BACKENDS`` under their ``name``.
    """

    #: Short identifier used by the CLI flag ``--backend`` and the
    #: ``env_backend`` setting.
    name: str = ""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.name:
            BACKENDS[cls.name] = cls

    # ------------------------------------------------------------------
    # Discovery / state
    # ------------------------------------------------------------------
    @abstractmethod
    def list_envs(self):
        """Return ``(active_env_name_or_None, list_of_all_env_names)``."""

    @abstractmethod
    def get_env_info(self, env_name):
        """Return a dict with at least ``version``, ``is_editable``,
        ``python_version`` for the given environment."""

    @abstractmethod
    def is_active_env_compatible(self):
        """Return True if the current process's env is compatible with this
        backend (e.g. ``CONDA_PREFIX`` is set for conda)."""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    @abstractmethod
    def create_env(self, env_name, *, benchmark=None, recreate=False,
                   pytest=False, empty=False, quiet=False):
        """Create the environment ``env_name`` (or ensure it exists).

        Returns
        -------
        fresh : bool
            ``True`` if the env was freshly created (or recreated via
            ``recreate=True``), ``False`` if an existing env was reused.
            Callers use this to skip per-class ``is_installed`` checks
            when nothing can be already installed.
        """

    @abstractmethod
    def delete_env(self, env_name):
        """Delete the environment ``env_name``."""

    # ------------------------------------------------------------------
    # Package install
    # ------------------------------------------------------------------
    @abstractmethod
    def can_install(self, requirement):
        """Return True if this backend can install ``requirement``.

        Used by ``DependenciesMixin.collect`` to skip-with-warn any class
        with a requirement the chosen backend cannot handle. Backends
        that translate everything (conda, requirements) return True
        for all inputs; backends with a narrower domain (uv) return
        False on conda-channel entries.
        """

    @abstractmethod
    def install_packages(self, *packages, env_name=None, quiet=False):
        """Install ``packages`` into ``env_name`` (current env if None)."""

    @abstractmethod
    def install_shell_script(self, script, *, env_name=None, quiet=False):
        """Run ``script`` as a shell install step inside ``env_name``."""

    # ------------------------------------------------------------------
    # Run inside env
    # ------------------------------------------------------------------
    @abstractmethod
    def run_in_env(self, script, *, env_name=None, raise_on_error=None,
                   capture_stdout=True, return_output=False):
        """Run ``script`` inside ``env_name`` and return its exit code
        (and optionally its output)."""

    # ------------------------------------------------------------------
    # Optional hooks (sensible defaults; only some backends override)
    # ------------------------------------------------------------------
    def verifies_install(self):
        """Return True if ``install_all_requirements`` should run the
        post-install verification loop (call ``cls.is_installed`` on each
        installed class). Backends that do not actually modify an
        environment — like ``requirements`` — return False.
        """
        return True

    def record_class_origin(self, klass_name, requirements, shell_scripts):
        """Hook called once per class while
        ``install_all_requirements`` collects requirements.

        Backends that need to attribute each requirement / install script
        back to the class that declared it (notably the ``requirements``
        backend, which annotates the manual-steps section of the export
        file) override this. The default is a no-op so conda / uv stay
        unchanged.

        Parameters
        ----------
        klass_name : str
            Display name of the class (Solver / Dataset / Objective).
        requirements : list of str
            ``requirements`` entries the class declared.
        shell_scripts : list of pathlib.Path
            Shell install scripts the class declared.
        """
        pass


def resolve_backend_name(cli_value=None):
    """Resolve which backend to use, in order:

    1. The ``cli_value`` argument (typically from ``--backend``).
    2. The ``BENCHOPT_ENV_BACKEND`` environment variable / ``env_backend``
       config setting.
    3. Auto-detection from the active shell env: ``CONDA_PREFIX`` →
       ``conda``; ``VIRTUAL_ENV`` (no ``CONDA_PREFIX``) → ``uv``.
    4. Default ``conda``.
    """
    if cli_value:
        return cli_value

    setting_value = get_setting("env_backend")
    if setting_value:
        return setting_value

    if os.environ.get("CONDA_PREFIX"):
        return "conda"
    if os.environ.get("VIRTUAL_ENV") and "uv" in BACKENDS:
        return "uv"
    return "conda"


def set_active_backend(name):
    """Pin the backend used by subsequent ``get_backend()`` calls."""
    global _active_backend_name
    if name not in BACKENDS:
        raise ValueError(
            f"Unknown backend {name!r}. Available: {sorted(BACKENDS)}"
        )
    _active_backend_name = name


def reset_active_backend():
    """Clear the active backend (mostly for tests)."""
    global _active_backend_name
    _active_backend_name = None


def get_backend(name=None):
    """Return the resolved :class:`EnvBackend` instance.

    Parameters
    ----------
    name : str, optional
        Explicit backend name. When ``None``, the active backend
        (set by :func:`set_active_backend`) is used; otherwise the
        backend is resolved via :func:`resolve_backend_name`.
    """
    if name is None:
        name = _active_backend_name
    if name is None:
        name = resolve_backend_name()

    if name not in BACKENDS:
        raise ValueError(
            f"Unknown backend {name!r}. Available: {sorted(BACKENDS)}"
        )
    return BACKENDS[name]()
