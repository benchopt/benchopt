import pytest

from benchopt.utils.conda_env_cmd import get_cmd_from_requirements
from benchopt.utils.conda_env_cmd import CONDA_CMD, PIP_CMD


# TODO: remove this test in benchopt 1.7
def test_deprecated_channel_spec():
    with pytest.warns(DeprecationWarning):
        cmd = get_cmd_from_requirements(["chan:pkg"])

    assert len(cmd) == 1
    assert cmd[0] == f"{CONDA_CMD} install --update-all -y -c chan pkg"

    with pytest.warns(DeprecationWarning):
        cmd = get_cmd_from_requirements(["pip:pkg"])

    assert len(cmd) == 1
    assert cmd[0] == f"{PIP_CMD} install pkg"

    with pytest.warns(DeprecationWarning):
        cmd = get_cmd_from_requirements(["pip:git+https://test.org"])

    assert len(cmd) == 1
    assert cmd[0] == f"{PIP_CMD} install git+https://test.org"

    with pytest.warns(DeprecationWarning):
        cmd = get_cmd_from_requirements(["pkg1", "chan:pkg2", "pip:pkg3"])

    assert len(cmd) == 2
    assert cmd[0] == f"{CONDA_CMD} install --update-all -y -c chan pkg1 pkg2"
    assert cmd[1] == f"{PIP_CMD} install pkg3"
