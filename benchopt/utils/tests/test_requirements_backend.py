"""Tests for the ``requirements`` (export-only) backend."""
import pytest

from benchopt.utils.env_management import (
    BACKENDS,
    RequirementsBackend,
    get_backend,
    reset_active_backend,
)


@pytest.fixture
def restore_backend():
    yield
    reset_active_backend()


def test_requirements_backend_registered():
    assert "requirements" in BACKENDS
    assert BACKENDS["requirements"] is RequirementsBackend


def test_get_requirements_backend(restore_backend):
    assert isinstance(get_backend("requirements"), RequirementsBackend)


# ---------------------------------------------------------------------------
# can_install (everything classified, nothing skipped)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("requirement", [
    "numpy",
    "pip::scikit-learn",
    "pytorch::pytorch",
    "conda-forge::scipy",
    "pkg=1.2",
])
def test_can_install_returns_true_for_everything(requirement):
    assert RequirementsBackend().can_install(requirement) is True


# ---------------------------------------------------------------------------
# install_packages classifies into pip vs manual
# ---------------------------------------------------------------------------

def test_install_packages_writes_pip_entries(tmp_path):
    out = tmp_path / "requirements.txt"
    RequirementsBackend.configure_output(output_path=str(out))
    RequirementsBackend().install_packages("numpy", "pip::scikit-learn")
    content = out.read_text()
    assert "numpy" in content
    assert "scikit-learn" in content
    # pip:: prefix must be stripped
    assert "pip::scikit-learn" not in content


def test_install_packages_records_channel_deps_as_manual(tmp_path):
    out = tmp_path / "requirements.txt"
    RequirementsBackend.configure_output(output_path=str(out))
    RequirementsBackend().install_packages(
        "numpy",
        "pytorch::pytorch",
        "conda-forge::scipy",
    )
    content = out.read_text()
    assert "numpy" in content
    # Channel-prefixed entries land in the manual-steps section.
    assert "Manual steps" in content
    assert "pytorch" in content
    assert "scipy" in content


def test_install_packages_dedupes(tmp_path):
    out = tmp_path / "requirements.txt"
    RequirementsBackend.configure_output(output_path=str(out))
    backend = RequirementsBackend()
    backend.install_packages("numpy", "pip::numpy")
    content = out.read_text()
    # Two paths to the same pip entry — only one line.
    assert content.count("numpy\n") == 1


def test_install_shell_script_writes_manual_line(tmp_path):
    out = tmp_path / "requirements.txt"
    RequirementsBackend.configure_output(output_path=str(out))
    RequirementsBackend().install_shell_script("/path/to/install.sh")
    content = out.read_text()
    assert "Manual steps" in content
    assert "install.sh" in content


def test_separate_manual_output(tmp_path):
    out = tmp_path / "requirements.txt"
    manual = tmp_path / "manual.txt"
    RequirementsBackend.configure_output(
        output_path=str(out), manual_output_path=str(manual),
    )
    RequirementsBackend().install_packages(
        "numpy", "pytorch::pytorch"
    )
    content = out.read_text()
    manual_content = manual.read_text()
    # When sidecar is used, no manual section in the main file.
    assert "numpy" in content
    assert "Manual steps" not in content
    assert "pytorch" in manual_content


def test_header_includes_benchmark_metadata(tmp_path):
    out = tmp_path / "requirements.txt"
    RequirementsBackend.configure_output(
        output_path=str(out),
        benchmark_name="my-bench",
        python_version="3.12",
    )
    RequirementsBackend().install_packages("numpy")
    content = out.read_text()
    assert "Benchmark: my-bench" in content
    assert "Python: 3.12" in content


# ---------------------------------------------------------------------------
# Env-management methods are no-ops / explicit errors
# ---------------------------------------------------------------------------

def test_create_env_raises():
    with pytest.raises(RuntimeError, match="does not create environments"):
        RequirementsBackend().create_env("foo")


def test_delete_env_raises():
    with pytest.raises(RuntimeError, match="does not manage environments"):
        RequirementsBackend().delete_env("foo")


def test_run_in_env_raises():
    with pytest.raises(NotImplementedError):
        RequirementsBackend().run_in_env("echo hi", env_name="foo")


def test_list_envs_returns_empty():
    assert RequirementsBackend().list_envs() == (None, [])


def test_is_active_env_compatible_is_true():
    assert RequirementsBackend().is_active_env_compatible() is True


# ---------------------------------------------------------------------------
# verifies_install / record_class_origin hooks
# ---------------------------------------------------------------------------

def test_verifies_install_is_false():
    # The export-only backend has no env to verify against.
    assert RequirementsBackend().verifies_install() is False


def test_conda_backend_verifies_install_is_true():
    # Sanity: the default conda backend still asks for verification.
    from benchopt.utils.env_management import CondaBackend
    assert CondaBackend().verifies_install() is True


def test_record_class_origin_attributes_manual_entries(tmp_path):
    out = tmp_path / "requirements.txt"
    RequirementsBackend.configure_output(output_path=str(out))
    backend = RequirementsBackend()
    backend.record_class_origin(
        "my-solver",
        ["pytorch::pytorch", "pip::numpy"],
        [],
    )
    backend.install_packages("pytorch::pytorch", "pip::numpy")
    content = out.read_text()
    # The manual section attributes the channel dep to its origin class.
    assert "from my-solver" in content
    # Pip-installable entries appear in the main list.
    assert "numpy" in content


def test_record_class_origin_attributes_shell_scripts(tmp_path):
    out = tmp_path / "requirements.txt"
    RequirementsBackend.configure_output(output_path=str(out))
    backend = RequirementsBackend()
    script = tmp_path / "install_radio.sh"
    script.write_text("#!/bin/bash\n")
    backend.record_class_origin("radio-solver", [], [script])
    backend.install_shell_script(script)
    content = out.read_text()
    assert "from radio-solver" in content
    assert "install_radio.sh" in content


# ---------------------------------------------------------------------------
# configure_output resets accumulators
# ---------------------------------------------------------------------------

def test_configure_output_resets_state(tmp_path):
    out = tmp_path / "first.txt"
    RequirementsBackend.configure_output(output_path=str(out))
    RequirementsBackend().install_packages("numpy")

    out2 = tmp_path / "second.txt"
    RequirementsBackend.configure_output(output_path=str(out2))
    RequirementsBackend().install_packages("scipy")

    # second.txt should not contain numpy (state was reset)
    assert "numpy" not in out2.read_text()
    assert "scipy" in out2.read_text()
