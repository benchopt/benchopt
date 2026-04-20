import pytest

from benchopt.utils.conda_env_cmd import get_env_file_from_requirements
from benchopt.utils.temp_benchmark import temp_benchmark


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


def test_deprecated_download_flag():
    """--download is a deprecated alias of --prepare."""
    with temp_benchmark() as bench:
        datasets = [(d, {}) for d in bench.get_datasets()]
        with pytest.warns(DeprecationWarning, match="--download.*deprecated"):
            bench.install_all_requirements(
                include_solvers=[],
                include_datasets=datasets,
                download=True,
                env_need_confirm=False,
            )
