import os
import re
import warnings
import configparser


CONFIG_FILE_LOCATION = os.environ.get('BENCHO_CONFIG', './benchopt.ini')

config = configparser.ConfigParser()
config.read(CONFIG_FILE_LOCATION)


DEFAULT_GLOBAL_CONFIG = {
    'debug': False,
    'allow_install': False,
    'raise_install_error': False,
    'github_token': None,
    'data_dir': './data/',
    'shell': os.environ.get('SHELL', 'bash')
}

DEFAULT_BENCHMARK_CONFIG = {
    'plots': "'suboptimality_curve'",
    'name': None
}


def get_global_setting(name):
    assert name in DEFAULT_GLOBAL_CONFIG, f"Unknown config key {name}"

    # Get the name of the environment variable associated to this setting
    env_var_name = f"BENCHO_{name.upper()}"

    if isinstance(DEFAULT_GLOBAL_CONFIG[name], bool):
        file_setting = config.getboolean('benchopt', name,
                                         fallback=DEFAULT_GLOBAL_CONFIG[name])
        setting = os.environ.get(env_var_name, file_setting)
        # convert string 0/1/true/false/yes/no/on/off to boolean
        if isinstance(setting, str):
            setting = setting.lower()
            try:
                setting = configparser.ConfigParser.BOOLEAN_STATES[setting]
            except KeyError:
                warnings.warn(
                    f'env variable {env_var_name} could not be parsed as a '
                    'boolean. Should be one of '
                    f'{list(configparser.ConfigParser.BOOLEAN_STATES.keys())}'
                )
                setting = file_setting
    else:
        # TODO: get the correct type from DEFAULT_GLOBAL_CONFIG for other types
        setting = config.get(
            'benchopt', name, fallback=DEFAULT_GLOBAL_CONFIG[name]
        )
        setting = os.environ.get(env_var_name, setting)

    return setting


def get_benchmark_setting(config_file, benchmark_name, setting_name):
    if not config_file.exists():
        config_file = CONFIG_FILE_LOCATION
    config = configparser.ConfigParser()
    config.read(config_file)

    # retrieve the setting value from the file or fallback to default.
    setting = config.get(
        benchmark_name, setting_name,
        fallback=DEFAULT_BENCHMARK_CONFIG[setting_name]
    )

    # Parse the setting depending on it name.
    if setting_name in ['plots']:
        setting = re.findall("[\"']([^']+)[\"']", setting)
    elif setting_name == 'name' and setting is None:
        setting = benchmark_name
    return setting


# Make sure we load the lattest value of the config parameter, even if it is
# changed. This should only be useful for testing purposes.
class BooleanFlag(object):
    def __init__(self, name):
        self.name = name

    def __bool__(self):
        return get_global_setting(self.name)


DEBUG = BooleanFlag('debug')
ALLOW_INSTALL = BooleanFlag('allow_install')
RAISE_INSTALL_ERROR = BooleanFlag('raise_install_error')
