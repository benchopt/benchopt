import click
import pprint
import tarfile
from pathlib import Path
from collections.abc import Iterable
import warnings
import json

from benchopt.config import set_setting
from benchopt.config import get_setting
from benchopt.benchmark import Benchmark
from benchopt.utils.files import rm_folder
from benchopt.utils.sys_info import get_sys_info
from benchopt.cli.completion import complete_benchmarks
from benchopt.cli.completion import complete_conda_envs
from benchopt.cli.completion import complete_datasets
from benchopt.cli.completion import complete_solvers
from benchopt.utils.conda_env_cmd import list_conda_envs
from benchopt.config import get_global_config_file
from benchopt.config import GLOBAL_CONFIG_FILE_MODE
from benchopt.utils.dynamic_modules import _load_class_from_module
from benchopt.utils.shell_cmd import _run_shell_in_conda_env
from benchopt.utils.terminal_output import colorify
from benchopt.utils.terminal_output import RED, GREEN, TICK, CROSS


ARCHIVE_ELEMENTS = [
    'README*', '*.yml', 'objective.py',
    'solvers/*', 'datasets/*', 'utils/**'
]

helpers = click.Group(
    name='Helpers',
    help="Helpers to clean and config ``benchopt``."
)


@helpers.command(
    help="Clean the cache and the outputs from a benchmark.",
    options_metavar=''
)
@click.argument('benchmark', default=Path.cwd(), type=click.Path(exists=True),
                shell_complete=complete_benchmarks)
@click.option("--filename", "-f", "filename",
              type=str, default="all",
              help="Name of the output file to remove.")
def clean(benchmark, token=None, filename='all'):

    benchmark = Benchmark(benchmark)
    # Delete result files
    output_folder = benchmark.get_output_folder()
    if output_folder.exists() and filename == 'all':
        print(f"rm -rf {output_folder}")
        rm_folder(output_folder)
    else:
        was_removed = False
        for ext in [".csv", ".html", ".parquet"]:
            if ext == ".html":
                to_remove = output_folder / f"{benchmark.name}_{filename}"
            else:
                to_remove = output_folder / filename
            file = to_remove.with_suffix(ext)
            if file.exists():
                was_removed = True
                print(f"rm {file}")
                file.unlink()
            json_path = output_folder / "cache_run_list.json"
            if was_removed and json_path.exists():
                print(f"Removing {filename}.{ext} entry from {json_path}")
                with open(json_path, "r") as cache_run:
                    json_file = json.load(cache_run)
                json_file.pop(f"{filename}.{ext}", None)
                with open(json_path, "w") as cache_run:
                    json.dump(json_file, cache_run)
    # Delete cache files
    print("Clear joblib cache")
    benchmark.mem.clear(warn=False)


def clean_archive(info):
    if "__pycache__" in info.name:
        return None

    # reset the username and info in the archive
    info.uid = info.gid = 0
    info.uname = info.gname = "benchopt"

    return info


@helpers.command(
    help="Create an archive of the benchmark that can easily be shared."
)
@click.argument('benchmark', default=Path.cwd(), type=click.Path(exists=True),
                shell_complete=complete_benchmarks)
@click.option('--with-outputs',
              is_flag=True,
              help="If this flag is set, also store the outputs of the "
              "benchmark in the archive.")
def archive(benchmark, with_outputs):

    benchmark = Benchmark(benchmark)
    bench_dir = benchmark.benchmark_dir

    to_archive = ARCHIVE_ELEMENTS
    if with_outputs:
        to_archive = to_archive + ['outputs/*']

    archive_name = f"{benchmark.name}.tar.gz"
    print(f"Creating {archive_name}...", end='', flush=True)
    with tarfile.open(archive_name, "w:gz") as tar:
        for elem_pattern in to_archive:
            for sub_elem in bench_dir.glob(elem_pattern):
                tar.add(sub_elem, sub_elem.relative_to(bench_dir.parent),
                        filter=clean_archive)
    print(f"done\nResults are in {archive_name}")


def check_conda_env(env_name, benchmark_name=None):
    """Return name of valid and existing conda environment.

    Parameters
    ----------
    env_name : str | None
        Expected name of conda environment to be used.
        If 'False', default conda environment name is returned.
        If 'True', benchmark specific conda environment, i.e.
        "benchopt_{benchmark_name}", is returned.
        If None, None is returned.
        Otherwise 'env_name' is returned.
        In any case but None, the conda environment existence is checked.
    benchmark_name : str | None
        Name of the benchmark that will be used.
        Unused unless env_name=='True'.

    Returns
    -------
    env_name : str | None
        Name of valid conda environment or None.
    """
    # Check conda env (if relevant)
    if env_name is not None:

        # Get a list of all conda envs
        default_conda_env, conda_envs = list_conda_envs()

        # If env_name is False (default), check availability
        # in the current environment.
        if env_name == 'False':
            # check if any current conda environment
            if default_conda_env is not None:
                env_name = default_conda_env
            else:
                raise RuntimeError("No conda environment is activated.")
        else:
            # If env_name is 'True', the flag `--env` has been used.
            # Check the conda env dedicated to the benchmark.
            # Else, use the <env_name> value.
            if env_name == 'True':
                env_name = f"benchopt_{benchmark_name}"
            else:
                # check provided <env_name>
                # (to avoid empty name like `--env-name ""`)
                if len(env_name) == 0:
                    raise RuntimeError("Empty environment name.")
                if env_name not in conda_envs:
                    raise RuntimeError(
                        f"{env_name} is not an existing conda environment."
                    )
    # output
    return env_name


def print_info(cls_name_list, cls_list, env_name=None, verbose=False):
    """Print information for each element of input listed

    Parameters
    ----------
    cls_name_list : list
        List of object names (solvers or datasets) to be printed.
    cls_list : list
        List of all objects (solvers or datasets) to print info from.
    env_name : str | None
        Name of conda environment where to check for object availability.
        If None or 'False', no check is made.
    verbose: bool
        If True, list object (solver or dataset) full descriptions (including
        name, parameters, dependencies and availability).
        If False, only list object (solver or dataset) names.
    """

    # select objects to print info from
    include_cls = []
    cls_name_list = [item.lower() for item in cls_name_list]
    if 'all' in cls_name_list:
        include_cls = cls_list
    else:
        include_cls = [
            item for item in cls_list if item.name.lower() in cls_name_list
        ]
    if not verbose:
        # short output
        name = [cls.name for cls in include_cls]
        print(f"{', '.join(map(str, name))}")
        print("-" * 10)
    else:
        # long output
        print("-" * 10)
        for cls in include_cls:
            print(f"## {cls.name}")
            # availability in env (if relevant)
            if env_name is not None:
                # check for dependency availability
                if env_name == "False":
                    disp_name = "running env"
                else:
                    disp_name = f"env: {env_name}"
                if cls.is_installed(env_name):
                    print(colorify(TICK, GREEN), end='', flush=True)
                    print(colorify(f" available in {disp_name}", GREEN))
                else:
                    print(colorify(CROSS, RED), end='', flush=True)
                    print(colorify(f" not available in '{disp_name}'", RED))
            # install command
            if hasattr(cls, 'requirements') and cls.requirements:
                print("> requirements:")
                packages = cls.requirements
                pip_packages = [pkg[4:] for pkg in packages
                                if pkg.startswith('pip:')]
                conda_packages = [pkg for pkg in packages
                                  if not pkg.startswith('pip:')]
                if len(conda_packages) > 0:
                    print("    conda install -c conda-forge "
                          f"{' '.join(conda_packages)}")
                if len(pip_packages) > 0:
                    print(f"    pip install {' '.join(pip_packages)}")
            else:
                print("> no dependencies")
            # doc
            if hasattr(cls, '__doc__') and cls.__doc__:
                print(f"> doc: {cls.__doc__}")
            # parameters
            if hasattr(cls, 'parameters') and cls.parameters:
                print("> parameters:")
                for param, value in cls.parameters.items():
                    values = ', '.join(map(str, value))
                    print(f"    {param}: {values}")

            print("-" * 10)


@helpers.command(
    help="List information (solvers/datasets) and corresponding requirements "
    "for a given benchmark."
)
@click.argument('benchmark', default=Path.cwd(), type=click.Path(exists=True),
                shell_complete=complete_benchmarks)
@click.option('--solver', '-s', 'solver_names',
              metavar="<solver_name>", multiple=True, type=str,
              help="Display information about <solver_name>. "
              "By default, all solvers are included except "
              "when -d flag is used. If -d flag is used, then "
              "no solver is included by default. "
              "When `-s` is used, only listed estimators are included. "
              "To include multiple solvers, use multiple `-s` options."
              "To include all solvers, use `-s 'all'` option. "
              "Using a `-s` option will trigger the verbose output.",
              shell_complete=complete_solvers)
@click.option('--dataset', '-d', 'dataset_names',
              metavar="<dataset_name>", multiple=True, type=str,
              help="Display information about <dataset_name>. By default, all "
              "datasets are included, except when -s flag is used. "
              "If -s flag is used, then no dataset is included. "
              "When `-d` is used, only listed datasets "
              "are included. Note that <dataset_name> can be a regexp. "
              "To include multiple datasets, use multiple `-d` options."
              "To include all datasets, use `-d 'all'` option."
              "Using a `-d` option will trigger the verbose output.",
              shell_complete=complete_datasets)
@click.option('--env', '-e', 'env_name',
              flag_value='True', type=str, default='False',
              help="Additional checks for requirement availability in "
              "the dedicated conda environment for the benchmark "
              "named 'benchopt_<BENCHMARK>'.")
@click.option('--env-name', 'env_name',
              metavar="<env_name>", type=str, default='False',
              shell_complete=complete_conda_envs,
              help="Additional checks for requirement availability in "
              "the conda environment named <env_name>.")
@click.option('--verbose', '-v',
              is_flag=True,
              help="If used, list solver/dataset "
              "parameters, dependencies and availability.")
def info(benchmark, solver_names, dataset_names, env_name='False',
         verbose=False):

    # benchmark
    benchmark = Benchmark(benchmark)
    print(f"Info regarding the benchmark '{benchmark.name}'")

    # validate solvers and datasets
    benchmark.validate_dataset_patterns(dataset_names)
    benchmark.validate_solver_patterns(solver_names)

    # get solvers and datasets in the benchmark
    all_solvers = benchmark.get_solvers()
    all_datasets = benchmark.get_datasets()
    # enable verbosity if any environment was provided
    if env_name is not None and env_name != 'False':
        verbose = True

    # conda env check only in verbose case
    if verbose:
        # Check conda env name
        env_name = check_conda_env(env_name, benchmark.name)
        # check conda environment validity
        check_benchopt = _run_shell_in_conda_env(
            "benchopt --version", env_name=env_name, capture_stdout=True
        )
        if check_benchopt != 0:
            warnings.warn(
                f"Environment '{env_name}' does not exist "
                "or is not configured for benchopt, "
                "benchmark requirement availability will not be checked, "
                "see the command `benchopt install`.",
                UserWarning
            )
            env_name = None
        else:
            print(
                "Checking benchmark requirement availability "
                f"in env '{env_name}'."
            )
            print(
                "Note: you can install all dependencies from a benchmark "
                "with the command `benchopt install`."
            )
    # enable verbosity if any solver/dataset are specified in input
    if dataset_names or solver_names:
        verbose = True

    # print information
    print("-" * 10)

    if not dataset_names and not solver_names:
        dataset_names = ['all']
        solver_names = ['all']
    if dataset_names:
        print("# DATASETS", flush=True)
        print_info(dataset_names, all_datasets, env_name, verbose)

    if solver_names:
        print("# SOLVERS", flush=True)
        print_info(solver_names, all_solvers, env_name, verbose)


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
              shell_complete=complete_benchmarks)
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
        config.touch(mode=GLOBAL_CONFIG_FILE_MODE)

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
@click.argument('benchmark', default=Path.cwd(), type=click.Path(exists=True),
                shell_complete=complete_benchmarks)
@click.argument('module_filename', nargs=1, type=Path)
@click.argument('base_class_name', nargs=1, type=str)
def check_install(benchmark, module_filename, base_class_name):

    # benchmark
    benchmark = Benchmark(benchmark)

    # Get class to check
    klass = _load_class_from_module(
        module_filename, base_class_name, benchmark.benchmark_dir
    )
    klass.is_installed(raise_on_not_installed=True)
