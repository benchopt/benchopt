import pytest

from benchopt.cli.main import run
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.utils.conda_env_cmd import get_env_file_from_requirements

from benchopt.tests.utils import CaptureCmdOutput


##############################################################################
# Deprecation check for benchopt 2.0
# XXX: remove in benchopt 2.0


def test_deprecated_channel_spec():
    with pytest.warns(DeprecationWarning):
        env = get_env_file_from_requirements(["chan:pkg"])
    assert env == (
        "channels:\n  - chan\n  - conda-forge\ndependencies:\n  - pkg"
    )

    with pytest.warns(DeprecationWarning):
        env = get_env_file_from_requirements(["pip:pkg"])
    assert env == "dependencies:\n  - pip\n  - pip:\n    - pkg"

    with pytest.warns(DeprecationWarning):
        env = get_env_file_from_requirements(["pip:git+https://test.org"])
    assert env == (
        "dependencies:\n  - pip\n  - pip:\n    - git+https://test.org"
    )

    with pytest.warns(DeprecationWarning):
        env = get_env_file_from_requirements(["pkg1", "chan:pkg2", "pip:pkg3"])
    assert env == (
        "channels:\n  - chan\n  - conda-forge\n"
        "dependencies:\n  - pkg1\n  - pkg2\n  - pip\n  - pip:\n    - pkg3"
    )

