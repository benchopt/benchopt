import click
from pathlib import Path

from benchopt.benchmark import Benchmark
from benchopt.utils.files import rm_folder
from benchopt.config import get_global_config_file
from benchopt.utils.dynamic_modules import _load_class_from_module


@click.group(name='HELPERS')
def helpers(ctx):
    "Private commands for benchopt."
    pass


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


@helpers.command(
    help="Configuration helper for benchopt."
)
@click.option('--benchmark', '-b', metavar='<benchmark>',
              type=click.Path(exists=True), default=None)
def config(benchmark, token=None, filename=None):

    if benchmark is None:
        global_config = get_global_config_file()
        print(f"Global config for benchopt is: {global_config.resolve()}")
    else:
        benchmark = Benchmark(benchmark)
        bench_config = benchmark.get_config_file()
        if not bench_config.exists():
            bench_config = get_global_config_file()
        print(
            f"Config File for benchmark {benchmark.name}: {bench_config}"
        )


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
