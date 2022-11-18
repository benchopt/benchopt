from benchopt.utils.conda_env_cmd import get_cmd_from_requirements
from benchopt.config import get_setting


CONDA_CMD = get_setting("conda_cmd")


def test_requirements_conda():

    packages = ["dep1", "dep2", "chan1:dep3"]
    cmd = get_cmd_from_requirements(packages)

    assert len(cmd) == 1
    cmd = cmd[0]

    assert CONDA_CMD in cmd, f"Should use {CONDA_CMD} to install deps."
    assert " dep1" in cmd, f"missing dep1 in cmd: {cmd}"
    assert " dep2" in cmd, f"missing dep2 in cmd: {cmd}"
    assert " dep3" in cmd, f"missing dep3 in cmd: {cmd}"
    assert " -c chan1 " in cmd, f"missing channel in cmd: {cmd}"


def test_requirements_pip():

    packages = ["pip:dep1", "pip:dep2"]
    cmd = get_cmd_from_requirements(packages)

    assert len(cmd) == 1
    cmd = cmd[0]

    assert 'pip' in cmd, "Should use pip to install deps."
    assert " dep1" in cmd, f"missing dep1 in cmd: {cmd}"
    assert " dep2" in cmd, f"missing dep2 in cmd: {cmd}"


def test_requirements_mixed():

    packages = ["dep1", "pip:dep2"]
    cmd = get_cmd_from_requirements(packages)

    assert len(cmd) == 2

    assert CONDA_CMD in cmd[0], f"Should use {CONDA_CMD} to install dep1."
    assert " dep1" in cmd[0], f"missing dep1 in cmd: {cmd[0]}"
    assert 'pip ' in cmd[1], "Should use pip to install dep2."
    assert " dep2" in cmd[1], f"missing dep2 in cmd: {cmd[1]}"
