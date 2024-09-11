import pytest

from benchopt.utils.conda_env_cmd import get_env_file_from_requirements


# TODO: remove this test in benchopt 1.7
def test_deprecated_channel_spec():

    with pytest.warns(DeprecationWarning):
        env = get_env_file_from_requirements(["chan:pkg"])
    assert env == "channels:\n  - chan\ndependencies:\n  - pkg"

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
        "channels:\n  - chan\n"
        "dependencies:\n  - pkg1\n  - pkg2\n  - pip\n  - pip:\n    - pkg3"
    )
