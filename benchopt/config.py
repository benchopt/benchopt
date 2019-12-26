import os
import re
import configparser


CONFIG_FILE_LOCATION = os.environ.get('BENCHO_CONFIG', './benchopt.ini')

config = configparser.ConfigParser()
config.read(CONFIG_FILE_LOCATION)


DEFAULT_GLOBAL = {
    'debug': False,
    'allow_install': False,
    'print_install_error': False,
    'venv_dir': './.venv/',
    'cache_dir': '.',
}

DEFAULT_BENCHMARK = {
    'exclude_solvers': "[]",
}


def get_global_setting(name):
    return config.get('benchopt', name, fallback=DEFAULT_GLOBAL[name])


def get_benchmark_setting(benchmark, name):
    result = config.get(benchmark, name, fallback=DEFAULT_BENCHMARK[name])
    if name == 'exclude_solvers':
        result = re.findall("[\"']([^']+)[\"']", result)
    return result
