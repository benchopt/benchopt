import pytest

from benchopt.utils.env_management import (
    BACKENDS,
    CondaBackend,
    get_backend,
    resolve_backend_name,
    set_active_backend,
    reset_active_backend,
)


@pytest.fixture
def restore_backend():
    """Reset the active backend after each test that mutates it."""
    yield
    reset_active_backend()


def test_conda_backend_is_registered():
    assert "conda" in BACKENDS
    assert BACKENDS["conda"] is CondaBackend


def test_get_backend_default_returns_conda(monkeypatch, restore_backend):
    # With no overrides, the backend resolves to conda (either via
    # CONDA_PREFIX auto-detect or the final fallback).
    monkeypatch.delenv("BENCHOPT_ENV_BACKEND", raising=False)
    backend = get_backend()
    assert backend.name == "conda"


def test_get_backend_with_explicit_name(restore_backend):
    backend = get_backend("conda")
    assert isinstance(backend, CondaBackend)


def test_get_backend_unknown_raises(restore_backend):
    with pytest.raises(ValueError, match="Unknown backend"):
        get_backend("nonexistent-backend")


def test_set_active_backend_persists(restore_backend):
    set_active_backend("conda")
    backend = get_backend()
    assert backend.name == "conda"


def test_set_active_backend_unknown_raises(restore_backend):
    with pytest.raises(ValueError, match="Unknown backend"):
        set_active_backend("nonexistent")


def test_resolve_cli_value_wins(monkeypatch, restore_backend):
    monkeypatch.setenv("BENCHOPT_ENV_BACKEND", "conda")
    assert resolve_backend_name("conda") == "conda"


def test_resolve_env_var_wins_over_autodetect(monkeypatch, restore_backend):
    monkeypatch.setenv("BENCHOPT_ENV_BACKEND", "conda")
    monkeypatch.delenv("CONDA_PREFIX", raising=False)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    assert resolve_backend_name() == "conda"


def test_resolve_autodetect_conda_prefix(monkeypatch, restore_backend):
    monkeypatch.delenv("BENCHOPT_ENV_BACKEND", raising=False)
    monkeypatch.setenv("CONDA_PREFIX", "/tmp/fake-env")
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    assert resolve_backend_name() == "conda"


def test_resolve_default_fallback(monkeypatch, restore_backend):
    monkeypatch.delenv("BENCHOPT_ENV_BACKEND", raising=False)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    assert resolve_backend_name() == "conda"


# ---------------------------------------------------------------------------
# CondaBackend.can_install
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("requirement", [
    "numpy",                  # bare conda name
    "pip::scikit-learn",      # pip-prefixed
    "pytorch::pytorch",       # conda channel
    "conda-forge::scipy",     # explicit conda-forge channel
    "package=1.2",            # version-pinned
    "pip::git+https://github.com/foo/bar",  # pip from git
])
def test_conda_can_install_everything(requirement):
    backend = CondaBackend()
    assert backend.can_install(requirement) is True


# ---------------------------------------------------------------------------
# Back-compat shims
# ---------------------------------------------------------------------------

def test_conda_env_cmd_shim_reexports():
    # Importing from the legacy path must still expose every function the
    # old module did, redirected to env_management.conda.
    from benchopt.utils import conda_env_cmd as legacy
    from benchopt.utils.env_management import conda as new

    for name in [
        "create_conda_env", "delete_conda_env", "list_conda_envs",
        "get_env_info", "install_in_conda_env", "shell_install_in_conda_env",
        "get_env_file_from_requirements", "_run_shell_in_conda_env",
        "DEFAULT_PYTHON_VERSION", "get_benchmark_python_version",
        "_python_version_conda_spec", "_python_version_satisfies",
        "BENCHOPT_ENV", "EMPTY_ENV", "CONDA_CMD",
    ]:
        assert getattr(legacy, name) is getattr(new, name)


def test_shell_cmd_run_in_conda_env_still_callable():
    # Old import path still works (back-compat shim).
    from benchopt.utils.shell_cmd import _run_shell_in_conda_env
    # Sanity: callable with env_name=None falls through to plain _run_shell.
    exit_code = _run_shell_in_conda_env("echo hello", env_name=None)
    assert exit_code == 0


def test_env_management_resolution_honors_BENCHOPT_ENV_BACKEND(
    monkeypatch, restore_backend,
):
    monkeypatch.setenv("BENCHOPT_ENV_BACKEND", "conda")
    name = resolve_backend_name()
    assert name == "conda"
