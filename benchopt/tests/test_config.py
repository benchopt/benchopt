import os
import pytest
from pathlib import Path
from contextlib import contextmanager

from benchopt.config import get_global_config_file


@contextmanager
def set_config_file(permission='600'):
    permission = int(f"100{permission}", base=8)
    config_file = Path() / 'test_config_file.ini'
    config_file.touch(mode=permission, exist_ok=False)
    old_config_file = os.environ.get('BENCHOPT_CONFIG', None)
    os.environ['BENCHOPT_CONFIG'] = str(config_file)
    try:
        yield config_file
    finally:
        if old_config_file is not None:
            os.environ['BENCHOPT_CONFIG'] = old_config_file
        else:
            del os.environ['BENCHOPT_CONFIG']
        config_file.unlink()


@pytest.mark.parametrize("permission", ["644", "655", "240"])
def test_config_file_permission_warn(permission):
    with set_config_file(permission) as config_file:
        msg = f"{config_file} is with mode {permission}"
        with pytest.warns(UserWarning, match=msg):
            global_config_file = get_global_config_file()
        assert str(global_config_file) == str(config_file)


def test_config_file_permission_no_warning():
    with set_config_file() as config_file:
        with pytest.warns(None) as record:
            global_config_file = get_global_config_file()
        assert str(global_config_file) == str(config_file)
        assert len(record) == 0, (
            "A warning was issued while it should not have.\n"
            f"Warning is: {record[0]}"
        )
