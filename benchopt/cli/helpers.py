import click
import pprint
from pathlib import Path
from collections import Iterable

from benchopt.config import set_setting
from benchopt.config import get_setting
from benchopt.benchmark import Benchmark
from benchopt.utils.files import rm_folder
from benchopt.utils.sys_info import get_sys_info
from benchopt.cli.completion import get_benchmark
from benchopt.config import get_global_config_file
from benchopt.utils.dynamic_modules import _load_class_from_module


helpers = click.Group(
    name='Helpers',
    help="Helpers to clean and config ``benchopt``."
)


@helpers.command(
    help="Clean the cache and the outputs from a benchmark.",
    options_metavar=''
)
@click.argument('benchmark', type=click.Path(exists=True),
                autocompletion=get_benchmark)
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
              type=click.Path(exists=True), default=None,
              autocompletion=get_benchmark)
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
