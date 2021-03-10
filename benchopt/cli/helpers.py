import os
import click
import pprint
from pathlib import Path
from collections import Iterable

from benchopt.config import set_setting
from benchopt.config import get_setting
from benchopt.benchmark import Benchmark
from benchopt.utils.files import rm_folder
from benchopt.utils.sys_info import get_sys_info
from benchopt.config import get_global_config_file
from benchopt.utils.dynamic_modules import _load_class_from_module
from benchopt.cli.main import get_benchmark
from benchopt.utils.shell_cmd import _run_shell_in_conda_env
from benchopt.utils.colorify import colorify
from benchopt.utils.colorify import RED, GREEN

helpers = click.Group(
    name='Helpers',
    help="Helpers to clean and config ``benchopt``."
)


@helpers.command(
    help="Clean the cache and the outputs from a benchmark.",
    options_metavar=''
)
@click.argument('benchmark', type=click.Path(exists=True))
def clean(benchmark, token=None, filename=None):

    benchmark = Benchmark(benchmark)

    # Delete result files
    output_folder = benchmark.get_output_folder()
    print(f"rm -rf {output_folder}")
    rm_folder(output_folder)

    # Delete cache files
    cache_folder = benchmark.get_cache_location()
    print(f"rm -rf {cache_folder}")
    rm_folder(cache_folder)


def print_info(cls_list, env_name=None):
    """Print information for each element of input listed

    Parameters
    ----------
    cls_list : list
        List of objects (solvers or datasets) to print info from.
    env_name : str | None
        name of environment where to check for object availability.
        If None or 'False', no check is made.
    """

    print("-" * 10)

    for cls in cls_list:
        print(f"## {cls.name}")
        # doc
        if hasattr(cls, '__doc__') and cls.__doc__ is not None and \
                len(cls.__doc__) > 0:
            print(f"- doc: {cls.__doc__}")
        # parameters
        if hasattr(cls, 'parameters') and cls.parameters is not None and \
                len(cls.parameters) > 0:
            print(f"- parameters: {', '.join(cls.parameters)}")
        # install command
        if hasattr(cls, 'install_cmd') and cls.install_cmd is not None:
            print(f"- install cmd: {cls.install_cmd}")
        else:
            print("- no installation required")
        # dependencies
        if hasattr(cls, 'requirements') and \
                cls.requirements is not None and \
                len(cls.requirements) > 0:
            print(f"- dependencies: {', '.join(cls.requirements)}")
        else:
            print("- no dependencies")
        # availability in env (if relevant)
        if env_name is not None and env_name != 'False':
            # check for dependency avaulability
            if cls.is_installed(env_name):
                print(colorify(u'\u2713', GREEN), end='', flush=True)
                print(colorify(f" available in env '{env_name}'", GREEN))
            else:
                print(colorify(u'\u274c', RED), end='', flush=True)
                print(colorify(f" not available in env '{env_name}'", RED))

        print("-" * 10)


@helpers.command(
    help="List information and requirements (solvers/datasets) "
    "for a given benchmark.",
    epilog="To (re-)install the required solvers and datasets "
    "in a benchmark-dedicated conda environment or in your own "
    "conda environment, see the command `benchopt install`."
)
@click.argument('benchmark', type=click.Path(exists=True),
                autocompletion=get_benchmark)
@click.option('--env', '-e', 'env_name',
              flag_value='True', type=str, default='False',
              help="Additional checks for requirement availability in "
              "the dedicated conda environment for the benchmark "
              "named 'benchopt_<BENCHMARK>'.")
@click.option('--env-name', 'env_name',
              metavar="<env_name>", type=str, default='False',
              help="Additional checks for requirement availability in "
              "the conda environment named <env_name>.")
def info(benchmark, env_name):

    benchmark = Benchmark(benchmark)
    print(f"Info regarding '{benchmark.name}'")

    # get solvers and datasets in the benchmark
    solvers = benchmark.list_benchmark_solvers()
    datasets = benchmark.list_benchmark_datasets()

    # Check conda env (if relevant)

    # If env_name is False (default), check availability
    # in the current environement.
    if env_name == 'False':
        # check if any current conda environment
        if 'CONDA_DEFAULT_ENV' in os.environ and \
                os.environ['CONDA_DEFAULT_ENV'] is not None and \
                len(os.environ['CONDA_DEFAULT_ENV']) > 0:
            # current conda env
            env_name = os.environ['CONDA_DEFAULT_ENV']
        else:
            msg = "No conda environment is activated. " + \
                "Activate one or use one of the options '-e/--env' " + \
                "or '--env-name'."
            raise RuntimeError(msg)
    else:
        # If env_name is True, the flag `--env` has been used. Check the conda
        # env dedicated to the benchmark. Else, use the <env_name> value.
        if env_name == 'True':
            env_name = f"benchopt_{benchmark.name}"
        else:
            # check provided <env_name>
            # (to avoid empty name like `--env-name ""`)
            if len(env_name) == 0:
                raise RuntimeError("Empty environment name.")

    # check if env_name exists
    if env_name is not None and env_name != 'False':
        check_benchopt = _run_shell_in_conda_env(
            "benchopt --version", env_name=env_name, capture_stdout=True
        )
        if check_benchopt != 0:
            msg = f"!! Environment '{env_name}' does not exist " + \
                "or is not configurated for benchopt, " + \
                "benchmark requirement availability will not be checked, " + \
                "see the command `benchopt install`."
            print(msg)
            env_name = None
        else:
            msg = "Checking benchamrk requirement availability " + \
                f"in env '{env_name}'."
            print(msg)

    # print information
    print("# Datasets", flush=True)
    print_info(datasets, env_name)

    print("# Solvers", flush=True)
    print_info(solvers, env_name)


@helpers.command()
def sys_info():
    "Get details on the system (processor, RAM, etc..)."
    pprint.pprint(get_sys_info())


@helpers.group(
    help="Configuration helper for benchopt. The configuration of benchopt "
    "is detailed in :ref:`config_doc`.",
    invoke_without_command=True
)
@click.option('--benchmark', '-b', metavar='<benchmark>',
              type=click.Path(exists=True), default=None)
@click.pass_context
def config(ctx, benchmark, token=None, filename=None):
    ctx.ensure_object(dict)

    if benchmark is None:
        config = get_global_config_file()
    else:
        benchmark = Benchmark(benchmark)
        config = benchmark.get_config_file()
    if ctx.invoked_subcommand is None:
        print(f"Config file is: {config.resolve()}")

    ctx.obj['config'] = config
    ctx.obj['benchmark_name'] = benchmark.name if benchmark else None


@config.command(help="Set value of setting <name> to <val>.\n\n"
                "Multiple values can be provided as separate arguments. "
                "This will generate a list of values in the config file.")
@click.option('--append', '-a', is_flag=True,
              help="Can be used to append values to the existing ones for "
              "settings that takes list of values.")
@click.argument("name", metavar='<name>', type=str)
@click.argument("values", metavar='<val>', type=str,
                nargs=-1, required=True)
@click.pass_context
def set(ctx, name, values, append=False):
    config = ctx.obj['config']
    benchmark_name = ctx.obj['benchmark_name']
    if not config.exists():
        config.parent.mkdir(exist_ok=True, parents=True)
        config.touch()

    if append:
        current_value = get_setting(
            name, config_file=config, benchmark_name=benchmark_name
        )
        if not isinstance(current_value, list):
            raise click.BadParameter(
                f"Cannot use option --append with setting '{name}' for which "
                "a string is expected."
            )
        current_value.extend(values)
        values = current_value

    if len(values) == 1:
        values = values[0]

    set_setting(name, values, config_file=config,
                benchmark_name=benchmark_name)


@config.command(help="Get config value for setting <name>.")
@click.argument("name", metavar='<name>', type=str)
@click.pass_context
def get(ctx, name):
    config = ctx.obj['config']
    benchmark_name = ctx.obj['benchmark_name']

    value = get_setting(
        name, config_file=config, benchmark_name=benchmark_name
    )
    if not isinstance(value, str) and isinstance(value, Iterable):
        value = ' '.join(value)
    print(f"{name}: {value}")


############################################################################
# Private sub-commands - not part of the public CLI
# These are helpers used in the other commands.

@helpers.command(
    help="Check that a given solver or dataset is correctly installed.\n\n"
    "The class to be checked is specified with the absolute path of the file "
    "in which it is defined MODULE_FILENAME and the name of the base "
    "class BASE_CLASS_NAME.",
    hidden=True
)
@click.argument('module_filename', nargs=1, type=Path)
@click.argument('base_class_name', nargs=1, type=str)
def check_install(module_filename, base_class_name):

    # Get class to check
    klass = _load_class_from_module(module_filename, base_class_name)
    klass.is_installed(raise_on_not_installed=True)
