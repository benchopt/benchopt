import os
import sys
import pytest
import warnings
from pathlib import Path
from contextlib import contextmanager

from benchopt.config import parse_value
from benchopt.config import DEFAULT_GLOBAL_CONFIG
from benchopt.config import DEFAULT_BENCHMARK_CONFIG
from benchopt.config import get_global_config_file
from benchopt.config import set_setting, get_setting
from benchopt.config import get_data_path
from benchopt.config import _check_settings


@pytest.fixture(autouse=True)
def reset_config_validation_flags():
    # Fixture to make sure that the config validation is run in each
    # configuration test, by resetting the flags that prevent skipping
    # the checks. Also makes sure that any BENCHOPT environment variables
    # are cleared before each test and restored after.
    DEFAULT_GLOBAL_CONFIG["_g_config_check"] = False
    DEFAULT_GLOBAL_CONFIG["_bench_config_check"] = False

    old_env = {
        k: v for k, v in os.environ.items()
        if k.startswith("BENCHOPT_") and k != "BENCHOPT_CONFIG"
    }
    for k in old_env:
        del os.environ[k]
    yield
    DEFAULT_GLOBAL_CONFIG["_g_config_check"] = False
    DEFAULT_GLOBAL_CONFIG["_bench_config_check"] = False
    os.environ.update(old_env)


@contextmanager
def temp_config_file(permission='600'):
    # Set a temporary global config file for benchopt with the specified
    # permission.
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


@pytest.mark.parametrize("setting_key", [
    k for k in DEFAULT_GLOBAL_CONFIG
    if k not in ["_g_config_check", "_bench_config_check"]
])
def test_config_file_set(setting_key):
    with temp_config_file(), warnings.catch_warnings():
        warnings.simplefilter("error")
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


def test_global_config_invalid_key_warns_once():
    with temp_config_file() as config_file:
        config_file.write_text("invalid_key: true\n")

        with pytest.warns(UserWarning, match="invalid_key is set"):
            _check_settings()

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            _check_settings()


def test_global_config_invalid_benchmark_section_type_warns():
    with temp_config_file() as config_file:
        config_file.write_text("my_benchmark: 1\n")

        with pytest.warns(UserWarning, match="my_benchmark is set"):
            _check_settings()


def test_global_config_invalid_benchmark_option_warns():
    with temp_config_file() as config_file:
        config_file.write_text(
            "my_benchmark:\n"
            "  invalid_bench_key: true\n"
        )

        with pytest.warns(UserWarning, match="invalid_bench_key is set"):
            _check_settings()


@pytest.mark.parametrize("option", DEFAULT_BENCHMARK_CONFIG.keys())
def test_global_config_valid_benchmark_option_no_warns(option):
    with temp_config_file() as config_file, warnings.catch_warnings():
        warnings.simplefilter("error")
        config_file.write_text(
            "my_benchmark:\n"
            f"  {option}: true\n"
        )

        _check_settings()


def test_global_config_invalid_env_variable_warns():
    with temp_config_file() as config_file:
        config_file.write_text("debug: false\n")

        os.environ["BENCHOPT_NOT_A_SETTING"] = "1"
        try:
            with pytest.warns(UserWarning, match="not_a_setting is set"):
                _check_settings()
        finally:
            del os.environ["BENCHOPT_NOT_A_SETTING"]


def test_benchmark_config_invalid_key_warns(tmp_path):
    config_file = tmp_path / "config.yml"
    config_file.write_text("invalid_bench_key: true\n")

    with pytest.warns(UserWarning, match="invalid_bench_key is set"):
        _check_settings(config_file=config_file, benchmark_name="dummy")


@pytest.mark.parametrize("pattern", ["~/test/", "$HOME/test/"])
@pytest.mark.parametrize("option", ["data_home", "dataset"])
def test_path_expansion_in_config(monkeypatch, option, pattern):
    """Test path expansion in config (~ and $ENV_VAR)."""

    with monkeypatch.context() as m, temp_config_file() as config_file:
        from benchopt.benchmark import _RUNNING_BENCHMARK
        m.setattr(_RUNNING_BENCHMARK, "get_config_file", lambda: config_file)
        m.setitem(os.environ, "HOME", "/path/to/home/")

        if option == "data_home":
            config = f"""data_home: {pattern}\n"""
        else:
            config = f"""data_paths:\n  dataset: {pattern}/dataset/\n"""
        config_file.write_text(config)
        path = get_data_path("dataset")

        assert path == Path("/path/to/home/test/dataset/")
