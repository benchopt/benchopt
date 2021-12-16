import os
import stat
import warnings
import configparser
from pathlib import Path
from collections.abc import Iterable
from benchopt.constants import PLOT_KINDS


BOOLEAN_STATES = configparser.ConfigParser.BOOLEAN_STATES
CONFIG_FILE_NAME = 'benchopt.ini'

# Global config file should be only accessible to current user as it stores
# sensitive information such as the Github token.
GLOBAL_CONFIG_FILE_MODE = stat.S_IFREG | stat.S_IRUSR | stat.S_IWUSR

DEFAULT_GLOBAL_CONFIG = {
    'debug': False,
    'raise_install_error': False,
    'github_token': None,
    'data_dir': './data/',
    'conda_cmd': 'conda',
    'shell': os.environ.get('SHELL', 'bash')
}
"""
* ``debug``: If set to true, enable debug logs.
* ``raise_install_error``, *boolean*: If set to true, raise error when
  install fails.
* ``github_token``, *str*: token to publish results on ``benchopt/results``
  via github.
* ``conda_cmd``, *str*: can be used to give the path to ``conda`` if it is
  not directly installed on ``$PATH``.
* ``shell``, *str*: can be used to specify the shell to use. Default to
  `SHELL` from env if it exists and ``'bash'`` otherwise.
"""

DEFAULT_BENCHMARK_CONFIG = {
    'plots': list(PLOT_KINDS),
}
"""
* ``plots``, *list*: Select the plots to display for the benchmark. Should be
  valid plot kinds. The list can simply be one item by line, with each item
  indented, as:

  .. code-block:: ini

    plots =
        suboptimality_curve
        histogram
"""


def get_global_config_file():
    "Return the global config file."

    config_file = os.environ.get('BENCHOPT_CONFIG', None)
    if config_file is not None:
        config_file = Path(config_file)
        assert config_file.exists(), (
            f"BENCHOPT_CONFIG is set but file {config_file} does not exists.\n"
            f"It can be created with `touch {config_file.resolve()}`."
        )
    else:
        config_file = Path('.') / CONFIG_FILE_NAME
        if not config_file.exists():
            config_file = Path.home() / '.config' / CONFIG_FILE_NAME

    # check that the global config file is only accessible to current user as
    # it stores critical information such as the github token.
    if (config_file.exists()
            and config_file.stat().st_mode != GLOBAL_CONFIG_FILE_MODE):
        mode = oct(config_file.stat().st_mode)[5:]
        expected_mode = oct(GLOBAL_CONFIG_FILE_MODE)[5:]
        warnings.warn(
            f"BenchOpt config file {config_file} is with mode {mode}.\n"
            "As it stores sensitive information such as the github token,\n"
            f"it is advised to use mode {expected_mode} (user rw only)."
        )

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

    # Create config file with the correct permission.
    if not config_file.exists():
        config_file.touch(mode=GLOBAL_CONFIG_FILE_MODE)

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
RAISE_INSTALL_ERROR = BooleanFlag('raise_install_error')
