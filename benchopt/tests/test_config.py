import os
import pytest
import warnings
from pathlib import Path
from contextlib import contextmanager

from benchopt.config import parse_value
from benchopt.config import DEFAULT_GLOBAL_CONFIG
from benchopt.config import get_global_config_file
from benchopt.config import set_setting, get_setting


@contextmanager
def set_config_file(permission='600'):
    permission = int(f"100{permission}", base=8)
    config_file = Path() / 'test_config_file.yml'
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


def test_parse_value():
    # Check boolean parsing
    for val in [True, 'true', 'True', '1', 'yes', 'on']:
        assert parse_value(val, True) is True
    for val in ['false', 'False', '0', 'no', 'off']:
        assert parse_value(val, True) is False

    # Check list parsing
    value = "test, test1\ntest2     \n test3"
    assert parse_value(value, []) == ['test', 'test1', 'test2', 'test3']

    # Check that if the default is not a bool or a list, we return the value
    assert parse_value(1, 2) == 1
    assert parse_value(2.0, 1) == 2.0
    assert parse_value('abc', 1) == 'abc'
    assert parse_value('abc', 'a') == 'abc'


@pytest.mark.parametrize("permission", ["644", "655", "240"])
def test_config_file_permission_warn(permission):
    with set_config_file(permission) as config_file:
        msg = f"{config_file} is with mode {permission}"
        with pytest.warns(UserWarning, match=msg):
            global_config_file = get_global_config_file()
        assert str(global_config_file) == str(config_file)


def test_config_file_permission_no_warning():
    with set_config_file() as config_file:
        with warnings.catch_warnings() as record:
            warnings.simplefilter("error")
            global_config_file = get_global_config_file()
        assert str(global_config_file) == str(config_file)


@pytest.mark.parametrize("setting_key", DEFAULT_GLOBAL_CONFIG)
def test_config_file_set(setting_key):
    with set_config_file() as config_file:
        default_value = DEFAULT_GLOBAL_CONFIG[setting_key]
        default_value = parse_value(os.environ.get(
            f"BENCHOPT_{setting_key.upper()}", default_value
        ), default_value)
        assert get_setting(setting_key) == default_value

        set_value = parse_value('True', default_value)
        set_setting(setting_key, set_value)
        assert get_setting(setting_key) == set_value


def test_config_file_set_error():
    with set_config_file() as config_file:
        with pytest.raises(SystemExit):
            set_setting('invalid_key', None)
