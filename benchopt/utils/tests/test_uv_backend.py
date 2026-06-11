"""Unit tests for the ``uv`` backend.

These tests cover the pure string / path logic and do not require ``uv``
to be installed. Backend-integration tests live in the parametrized
install test suite and are skipped when ``uv`` is unavailable.
"""
import os
import shutil
from pathlib import Path

import pytest

from benchopt.utils.env_management import (
    BACKENDS,
    UvBackend,
    get_backend,
    resolve_backend_name,
    reset_active_backend,
)


requires_uv = pytest.mark.skipif(
    shutil.which("uv") is None,
    reason="uv is not installed on PATH",
)


@pytest.fixture
def restore_backend():
    yield
    reset_active_backend()


def test_uv_backend_registered():
    assert "uv" in BACKENDS
    assert BACKENDS["uv"] is UvBackend


def test_get_uv_backend(restore_backend):
    assert isinstance(get_backend("uv"), UvBackend)


# ---------------------------------------------------------------------------
# can_install
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("requirement, expected", [
    ("numpy", True),
    ("pip::scikit-learn", True),
    ("pip::git+https://github.com/foo/bar", True),
    ("pkg=1.2", True),
    ("pkg>=1.2", True),
    ("pytorch::pytorch", False),
    ("conda-forge::scipy", False),
    # Legacy single-colon syntax (deprecated but still parseable):
    ("pip:scikit-learn", True),
    ("chan:foo", False),
])
def test_can_install(requirement, expected):
    assert UvBackend().can_install(requirement) is expected


# ---------------------------------------------------------------------------
# Env path resolution
# ---------------------------------------------------------------------------

def test_envs_dir_uses_xdg_home(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert UvBackend.envs_dir() == tmp_path / "benchopt" / "envs"


def test_envs_dir_falls_back_to_local_share(monkeypatch):
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    expected = Path.home() / ".local" / "share" / "benchopt" / "envs"
    assert UvBackend.envs_dir() == expected


def test_env_path_bare_name_in_envs_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert (
        UvBackend.env_path("my-env")
        == tmp_path / "benchopt" / "envs" / "my-env"
    )


def test_env_path_absolute_used_as_is(tmp_path):
    p = tmp_path / "explicit"
    assert UvBackend.env_path(str(p)) == p


def test_env_path_none_uses_virtual_env(monkeypatch, tmp_path):
    monkeypatch.setenv("VIRTUAL_ENV", str(tmp_path))
    assert UvBackend.env_path(None) == tmp_path


def test_env_path_none_without_virtual_env_raises(monkeypatch):
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    with pytest.raises(RuntimeError, match="No env_name"):
        UvBackend.env_path(None)


# ---------------------------------------------------------------------------
# list_envs
# ---------------------------------------------------------------------------

def test_list_envs_enumerates_envs_dir(monkeypatch, tmp_path):
    envs_dir = tmp_path / "benchopt" / "envs"
    envs_dir.mkdir(parents=True)
    (envs_dir / "alpha").mkdir()
    (envs_dir / "beta").mkdir()
    (envs_dir / "a-file").write_text("")  # ignored
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)

    active, all_envs = UvBackend().list_envs()
    assert active is None
    assert all_envs == ["alpha", "beta"]


def test_list_envs_marks_active(monkeypatch, tmp_path):
    envs_dir = tmp_path / "benchopt" / "envs"
    envs_dir.mkdir(parents=True)
    (envs_dir / "alpha").mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("VIRTUAL_ENV", str(envs_dir / "alpha"))

    active, all_envs = UvBackend().list_envs()
    assert active == "alpha"
    assert all_envs == ["alpha"]


# ---------------------------------------------------------------------------
# is_active_env_compatible
# ---------------------------------------------------------------------------

def test_is_active_env_compatible(monkeypatch, tmp_path):
    monkeypatch.setenv("VIRTUAL_ENV", str(tmp_path))
    assert UvBackend().is_active_env_compatible() is True


def test_is_active_env_compatible_false(monkeypatch):
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    assert UvBackend().is_active_env_compatible() is False


# ---------------------------------------------------------------------------
# Resolution chain (uv autodetect)
# ---------------------------------------------------------------------------

def test_resolve_autodetect_virtual_env(monkeypatch, restore_backend):
    monkeypatch.delenv("BENCHOPT_ENV_BACKEND", raising=False)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)
    monkeypatch.setenv("VIRTUAL_ENV", "/tmp/fake-venv")
    assert resolve_backend_name() == "uv"


def test_resolve_conda_wins_over_virtual_env(monkeypatch, restore_backend):
    # Defensive: if both are set, conda takes precedence.
    monkeypatch.delenv("BENCHOPT_ENV_BACKEND", raising=False)
    monkeypatch.setenv("CONDA_PREFIX", "/tmp/conda-env")
    monkeypatch.setenv("VIRTUAL_ENV", "/tmp/uv-venv")
    assert resolve_backend_name() == "conda"


# ---------------------------------------------------------------------------
# Integration smoke test (needs uv binary)
# ---------------------------------------------------------------------------

@requires_uv
def test_uv_create_and_install_smoke(tmp_path):
    """End-to-end: create an empty uv venv and pip-install a package."""
    env_name = str(tmp_path / "smoke-env")
    backend = UvBackend()
    try:
        backend.create_env(env_name, empty=True, quiet=True)
        # The created env should have a python binary.
        from benchopt.utils.env_management.uv import _venv_python
        assert os.path.exists(_venv_python(env_name))
        # Install a trivial pure-Python package.
        backend.install_packages("six", env_name=env_name, quiet=True)
        exit_code = backend.run_in_env(
            'python -c "import six; print(six.__version__)"',
            env_name=env_name,
        )
        assert exit_code == 0
    finally:
        backend.delete_env(env_name)
