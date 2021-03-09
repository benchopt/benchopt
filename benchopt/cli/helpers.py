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
from benchopt.cli.completion import get_benchmark
from benchopt.config import get_global_config_file
from benchopt.utils.dynamic_modules import _load_class_from_module
from benchopt.utils.shell_cmd import create_conda_env
from benchopt.cli.main import get_solvers, get_datasets, get_benchmark


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


@helpers.command(
    help="Install the requirements (solvers/datasets) for a benchmark."
)
@click.argument('benchmark', type=click.Path(exists=True),
                autocompletion=get_benchmark)
@click.option('--force', '-f',
              is_flag=True,
              help="If this flag is set, the reinstallation of "
              "the benchmark requirements is forced.")
@click.option('--solver', '-s', 'solver_names',
              metavar="<solver_name>", multiple=True, type=str,
              help="Include <solver_name> in the installation. "
              "By default, all solvers are included. "
              "When `-s` is used, only listed estimators are included. "
              "To include multiple solvers, use multiple `-s` options.",
              autocompletion=get_solvers)
@click.option('--dataset', '-d', 'dataset_names',
              metavar="<dataset_name>", multiple=True, type=str,
              help="Install the dataset <dataset_name>. By default, all "
              "datasets are included. When `-d` is used, only listed datasets "
              "are included. Note that <dataset_name> can be a regexp. "
              "To include multiple datasets, use multiple `-d` options.",
              autocompletion=get_datasets)
@click.option('--env', '-e', 'env_name',
              flag_value='True', type=str, default='False',
              help="Install all requirements in a dedicated "
              "conda environment for the benchmark. "
              "The environment is named 'benchopt_<BENCHMARK>' and all "
              "solver dependencies and datasets are installed in it.")
@click.option('--env-name', 'env_name',
              metavar="<env_name>", type=str, default='False',
              help="Install the benchmark requirements in the "
              "conda environment named <env_name>. "
              "If not existing, it is created.")
@click.option('--recreate',
              is_flag=True,
              help="If this flag is set, start with a fresh conda "
              "environment. It can only be used combined with options "
              "`-e/--env` or `--env-name`.")
@click.option('--yes', '-y', 'confirm',
              is_flag=True,
              help="If this flag is set, no confirmation will be asked "
              "to the user to install requirements in the current environment."
              " Useless with options `-e/--env` or `--env-name`.")
def install(benchmark, solver_names, dataset_names, force=False,
            recreate=False, env_name='False', confirm=False):

    # Check that the dataset/solver patterns match actual dataset
    benchmark = Benchmark(benchmark)
    print(f"Installing '{benchmark.name}' requirements")
    benchmark.validate_dataset_patterns(dataset_names)
    benchmark.validate_solver_patterns(solver_names)

    # If env_name is False (default), installation in the current environement.
    if env_name == 'False':
        # incompatible with the 'recreate' flag to avoid messing with the
        # user environement
        if recreate:
            msg = "Cannot recreate conda env without using options " + \
                "'-e/--env' or '--env-name'."
            raise RuntimeError(msg)
        # check if any current conda environment
        if 'CONDA_DEFAULT_ENV' in os.environ and \
                os.environ['CONDA_DEFAULT_ENV'] is not None and \
                len(os.environ['CONDA_DEFAULT_ENV']) > 0:
            # current conda env
            env_name = os.environ['CONDA_DEFAULT_ENV']
            # ask for user confirmation to install in current conda env
            if not confirm:
                click.confirm(f"Install in the current env '{env_name}'?",
                              abort=True)
        else:
            raise RuntimeError("No conda environment is activated.")
    else:
        # If env_name is True, the flag `--env` has been used. Create a conda
        # env specific to the benchmark. Else, use the <env_name> value.
        if env_name == 'True':
            env_name = f"benchopt_{benchmark.name}"
        else:
            # check provided <env_name>
            # (to avoid empty name like `--env-name ""`)
            if len(env_name) == 0:
                raise RuntimeError("Empty environment name.")
            # avoid recreating 'base' conda env`
            if env_name == 'base' and recreate:
                raise RuntimeError(
                    "Impossible to recreate 'base' conda environment."
                )

        # create environment if necessary
        create_conda_env(env_name, recreate=recreate)

    # If force is True (default is False), it forces the reinstallation of
    # selected solvers (all solvers from the benchmark by default)
    forced_solvers = ()
    if force:
        if len(solver_names) > 0:
            forced_solvers = solver_names
        else:
            forced_solvers = benchmark.list_benchmark_solver_names()
    # same for datasets
    forced_datasets = ()
    if force:
        if len(dataset_names) > 0:
            forced_datasets = dataset_names
        else:
            forced_datasets = benchmark.list_benchmark_dataset_names()

    # install required datasets
    print("# Datasets", flush=True)
    benchmark.install_required_datasets(
        dataset_names, forced_datasets=forced_datasets, env_name=env_name
    )

    # install required solvers
    print("# Solvers", flush=True)
    benchmark.install_required_solvers(
        solver_names, forced_solvers=forced_solvers, env_name=env_name
    )


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
