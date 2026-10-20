import pytest

from benchopt.utils.shell_cmd import _split_shell
from benchopt.utils.conda_env_cmd import get_env_file_from_requirements
from benchopt.config import get_setting


CONDA_CMD = get_setting("conda_cmd")


@pytest.mark.parametrize("shell, expected", [
    ("cmd /c", ["cmd", "/c"]),
    ("bash --norc --noprofile", ["bash", "--norc", "--noprofile"]),
    ("bash", ["bash"]),
])
def test_split_shell(shell, expected):
    # The shell setting carries its arguments, so it must be split (not quoted
    # as a whole) before being handed to subprocess.
    assert _split_shell(shell) == expected


def test_split_shell_spaced_path(monkeypatch):
    # A shell path that contains spaces (e.g. Git Bash on Windows) must be
    # expressible by quoting it, and the quotes stripped so it resolves.
    monkeypatch.setattr("benchopt.utils.shell_cmd.sys.platform", "win32")
    shell = '"C:\\Program Files\\Git\\bin\\bash.EXE" --norc'
    assert _split_shell(shell) == [
        "C:\\Program Files\\Git\\bin\\bash.EXE", "--norc"
    ]


def test_requirements_conda():

    packages = ["dep1", "dep2"]
    env = get_env_file_from_requirements(packages)
    assert env == (
        "channels:\n  - conda-forge\n"
        "dependencies:\n  - dep1\n  - dep2"
    )


def test_requirements_conda_with_channels():
    packages = ["dep1", "dep2", "chan1::dep3", "chan2::dep4", "chan1::dep2"]
    env = get_env_file_from_requirements(packages)
    assert env == (
        "channels:\n  - chan1\n  - chan2\n  - conda-forge\n"
        "dependencies:\n  - dep1\n  - dep2\n  - dep3\n  - dep4"
    )


def test_requirements_pip():

    packages = ["pip::dep1", "pip::dep2"]
    env = get_env_file_from_requirements(packages)
    assert env == (
        "dependencies:\n  - pip\n"
        "  - pip:\n    - dep1\n    - dep2"
    )


def test_requirements_mixed():

    packages = ["dep1", "chan1::dep2", "pip::dep2", "pip::dep2"]
    env = get_env_file_from_requirements(packages)
    assert env == (
        "channels:\n  - chan1\n  - conda-forge\n"
        "dependencies:\n  - dep1\n  - dep2\n"
        "  - pip\n  - pip:\n    - dep2"
    )
