from benchopt.utils.conda_env_cmd import get_env_file_from_requirements
from benchopt.config import get_setting


CONDA_CMD = get_setting("conda_cmd")


def test_requirements_conda():

    packages = ["dep1", "dep2"]
    env = get_env_file_from_requirements(packages)
    assert env == "dependencies:\n  - dep1\n  - dep2"


def test_requirements_conda_with_channels():
    packages = ["dep1", "dep2", "chan1::dep3", "chan2::dep4", "chan1::dep2"]
    env = get_env_file_from_requirements(packages)
    assert env == (
        "channels:\n  - chan1\n  - chan2\n"
        "dependencies:\n  - dep1\n  - dep2\n  - dep3\n  - dep4"
    )


def test_requirements_pip():

    packages = ["pip::dep1", "pip::dep2"]
    env = get_env_file_from_requirements(packages)
    assert env == "dependencies:\n  - pip\n  - pip:\n    - dep1\n    - dep2"


def test_requirements_mixed():

    packages = ["dep1", "chan1::dep2", "pip::dep2", "pip::dep2"]
    env = get_env_file_from_requirements(packages)
    assert env == (
        "channels:\n  - chan1\ndependencies:\n  - dep1\n  - dep2\n"
        "  - pip\n  - pip:\n    - dep2"
    )
