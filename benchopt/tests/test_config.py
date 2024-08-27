import os
import sys
import pytest
import warnings
from pathlib import Path
from contextlib import contextmanager

from benchopt.config import parse_value
from benchopt.config import DEFAULT_GLOBAL_CONFIG
from benchopt.config import get_global_config_file
from benchopt.config import set_setting, get_setting


@contextmanager
def temp_config_file(permission='600'):
    permission = int(f"100{permission}", base=8)
    config_file = Path(Path() / 'test_config_file.yml')
    if sys.platform != 'win32':
        config_file.touch(mode=permission, exist_ok=False)
    else:
        config_file.touch(exist_ok=False)
        if permission == 0o600:
            os.chmod(config_file, 0o600)
        else:
            os.chmod(config_file, 0o666)
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
    assert parse_value('abc', 'a') == 'abc'


# Skip this test on Windows
@pytest.mark.skipif(sys.platform == 'win32',
                    reason="Skipping Unix-specific test on Windows")
@pytest.mark.parametrize("permission", ["644", "655", "240"])
def test_config_file_permission_warn_unix(permission):
    with temp_config_file(permission) as config_file:
        msg = f"{config_file} is with mode {permission}"
        with pytest.warns(UserWarning, match=msg):
            global_config_file = get_global_config_file()
        assert str(global_config_file) == str(config_file)


# Windows-specific test
@pytest.mark.skipif(sys.platform != 'win32',
                    reason="Skipping Windows-specific test on Unix systems")
@pytest.mark.parametrize("permission", ["666"])
def test_config_file_permission_warn_windows(permission):
    with temp_config_file(permission) as config_file:
        msg = f"{config_file} is with mode {permission}"
        with pytest.warns(UserWarning, match=msg):
            global_config_file = get_global_config_file()
        assert str(global_config_file) == str(config_file)


@pytest.mark.skipif(sys.platform == 'win32',
                    reason="Skipping Unix-specific test on Windows")
def test_config_file_permission_no_warning():
    with temp_config_file() as config_file:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            global_config_file = get_global_config_file()
        assert str(global_config_file) == str(config_file)


@pytest.mark.parametrize("setting_key", DEFAULT_GLOBAL_CONFIG)
def test_config_file_set(setting_key):
    with temp_config_file():
        default_value = DEFAULT_GLOBAL_CONFIG[setting_key]
        default_value = parse_value(os.environ.get(
            f"BENCHOPT_{setting_key.upper()}", default_value
        ), default_value)
        assert get_setting(setting_key) == default_value

        # pick arbitrary new and env values for this configuration parameter
        if isinstance(default_value, (bool, str)) or default_value is None:
            set_value = parse_value('True', default_value)
            env_value = parse_value('False', default_value)
        else:
            set_value = parse_value(2 * default_value + 1, default_value)
            env_value = parse_value(2 * default_value - 1, default_value)

        set_setting(setting_key, set_value)

        # Make sure the value is correctly set and retrieved
        try:
            # If the env var is not set, we should get the set value
            old_value = os.environ.pop(f"BENCHOPT_{setting_key.upper()}", None)
            assert get_setting(setting_key) == set_value

            # Otherwise, we get the env value
            os.environ[f"BENCHOPT_{setting_key.upper()}"] = str(env_value)
            assert get_setting(setting_key) == env_value
            del os.environ[f"BENCHOPT_{setting_key.upper()}"]
        finally:
            if old_value is not None:
                os.environ[f"BENCHOPT_{setting_key.upper()}"] = old_value


def test_config_file_set_error():
    with temp_config_file():
        with pytest.raises(SystemExit):
            set_setting('invalid_key', None)
