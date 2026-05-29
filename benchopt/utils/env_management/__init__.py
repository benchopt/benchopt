"""Backend-aware environment management for ``benchopt install``.

Provides the :class:`EnvBackend` protocol and built-in backends
(``conda``, plus future ``uv`` / ``requirements``). Use :func:`get_backend`
to obtain the resolved backend for the current invocation.
"""

from .base import (
    EnvBackend,
    BACKENDS,
    get_backend,
    set_active_backend,
    reset_active_backend,
    resolve_backend_name,
)
from .python_version import (
    DEFAULT_PYTHON_VERSION,
    get_benchmark_python_version,
    _python_version_satisfies,
)
from .conda import CondaBackend
from .uv import UvBackend
from .requirements import RequirementsBackend

__all__ = [
    "EnvBackend",
    "BACKENDS",
    "get_backend",
    "set_active_backend",
    "reset_active_backend",
    "resolve_backend_name",
    "CondaBackend",
    "UvBackend",
    "RequirementsBackend",
    "DEFAULT_PYTHON_VERSION",
    "get_benchmark_python_version",
    "_python_version_satisfies",
]
