import os
import warnings
import configparser
from pathlib import Path
from collections import Iterable

BOOLEAN_STATES = configparser.ConfigParser.BOOLEAN_STATES
CONFIG_FILE_NAME = 'benchopt.ini'
CONFIG_FILE_LOCATION = os.environ.get('BENCHO_CONFIG', './benchopt.ini')

DEFAULT_GLOBAL_CONFIG = {
    'debug': False,
    'allow_install': False,
    'raise_install_error': False,
    'github_token': None,
    'data_dir': './data/',
    'conda_cmd': 'conda',
    'shell': os.environ.get('SHELL', 'bash')
}

DEFAULT_BENCHMARK_CONFIG = {
    'plots': ["suboptimality_curve"],
}


def get_global_config_file():
    "Return the global config file."

    config_file = os.environ.get('BENCHOPT_CONFIG', None)
    if config_file is not None:
        config_file = Path(config_file)
        assert config_file.exists(), (
            f"BENCHOPT_CONFIG is set but file {config_file} does not exists."
        )
        return config_file
    config_file = Path('.') / CONFIG_FILE_NAME
    if not config_file.exists():
        config_file = Path.home() / '.config' / CONFIG_FILE_NAME
    return config_file


def set_setting(name, value, config_file=None, benchmark_name=None):
    if config_file is None:
        config_file = get_global_config_file()

    # Get default value
    default_config = DEFAULT_BENCHMARK_CONFIG
    if benchmark_name is None:
        benchmark_name = 'benchopt'
        default_config = DEFAULT_GLOBAL_CONFIG

    if name not in default_config:
        print(
            f'ERROR: {name} is not a setting for {benchmark_name}. Possible '
            'settings are:\n  - ' + '\n  - '.join(default_config)
        )
        raise SystemExit(1)
    default_value = default_config[name]

    # Get global config file
    config = configparser.ConfigParser()
    config.read(config_file)

    if benchmark_name not in config:
        config[benchmark_name] = {}

    config[benchmark_name][name] = reverse_parse(default_value, value)
    with config_file.open('w') as f:
        config.write(f)


def get_setting(name, config_file=None, benchmark_name=None):
    if config_file is None:
        config_file = get_global_config_file()

    # Get default value
    default_config = DEFAULT_BENCHMARK_CONFIG
    if benchmark_name is None:
        benchmark_name = 'benchopt'
        default_config = DEFAULT_GLOBAL_CONFIG
    assert name in default_config, f"Unknown config key {name}"
    default_value = default_config[name]

    # Get config file
    config = configparser.ConfigParser()
    config.read(config_file)

    # Get the name of the environment variable associated to this setting
    env_var_name = f"BENCHOPT_{name.upper()}"

    # Get setting with order: 1. env var / 2. config file / 3. default value
    value = config.get(benchmark_name, name, fallback=default_value)
    value = os.environ.get(env_var_name, value)

    # Parse the value to the correct type
    value = parse_value(default_value, value)

    return value


def parse_value(default_value, value):
    if isinstance(default_value, bool):
        # convert string 0/1/true/false/yes/no/on/off to boolean
        if isinstance(value, str):
            value = value.lower()
            try:
                value = BOOLEAN_STATES[value]
            except KeyError:
                warnings.warn(
                    f'setting {value} could not be parsed as a '
                    'boolean. Should be one of '
                    f'{list(BOOLEAN_STATES.keys())}'
                )
                value = default_value
        assert isinstance(value, bool)
    elif isinstance(default_value, list):
        # parse multiline statements as list with separators '\n' and ','
        if isinstance(value, str):
            values = value.split()
            values = [v.strip() for value in values
                      for v in value.split(',') if v != '']
            value = values
        assert isinstance(value, list)

    return value


def reverse_parse(default_value, value):
    if isinstance(value, bool) or isinstance(default_value, bool):
        if isinstance(value, bool):
            assert isinstance(default_value, bool)
            value = 'true' if value else 'false'
        else:
            assert value.lower() in BOOLEAN_STATES, (
                "boolean setting should have value in "
                f"{list(BOOLEAN_STATES.keys())}"
            )
    elif isinstance(value, Iterable) and not isinstance(value, str):
        assert isinstance(default_value, list)
        value = '\n' + '\n'.join(value)

    return value


# Make sure we load the lattest value of the config parameter, even if it is
# changed. This should only be useful for testing purposes.
class BooleanFlag(object):
    def __init__(self, name):
        self.name = name

    def __bool__(self):
        return get_setting(self.name)


DEBUG = BooleanFlag('debug')
ALLOW_INSTALL = BooleanFlag('allow_install')
RAISE_INSTALL_ERROR = BooleanFlag('raise_install_error')
