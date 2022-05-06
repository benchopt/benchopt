import yaml
import click
import warnings
from pathlib import Path

from benchopt.benchmark import Benchmark
from benchopt.cli.completion import complete_solvers
from benchopt.cli.completion import complete_datasets
from benchopt.cli.completion import complete_benchmarks
from benchopt.cli.completion import complete_conda_envs
from benchopt.utils.conda_env_cmd import list_conda_envs
from benchopt.utils.conda_env_cmd import create_conda_env
from benchopt.utils.shell_cmd import _run_shell_in_conda_env
from benchopt.utils.conda_env_cmd import get_benchopt_version_in_env
from benchopt.utils.profiling import print_stats


main = click.Group(
    name='Principal Commands',
    help="Principal commands that are used in ``benchopt``."
)


def _get_run_args(cli_kwargs, config_file_kwargs):
    ctx = click.get_current_context()
    for k, v in config_file_kwargs.items():
        # click maps options names to variable names by removing '--' and
        # replacing '-' by '_'. We use the same mapping to convert options from
        # config_file, so that variable names match
        var_name = k.replace('-', '_')

        if var_name not in cli_kwargs:
            raise ValueError(
                f"Invalid config file option {k}. "
                "See list of valid options with `benchopt run -h`.")

        # only override CLI variables if they have their default value
        if (ctx.get_parameter_source(var_name) is not None and
                ctx.get_parameter_source(var_name).name == 'DEFAULT'):
            cli_kwargs[var_name] = v

    return_names = [
        "benchmark",
        "solver",
        "force_solver",
        "dataset",
        "objective",
        "max_runs",
        "n_repetitions",
        "timeout",
        "n_jobs",
        "plot",
        "html",
        "pdb",
        "profile",
        "env_name",
        "objective_filter",
        "old_objective_filter",
    ]
    return [cli_kwargs[name] for name in return_names]


@main.command(
    help="Run a benchmark with benchopt.",
    epilog="To (re-)install the required solvers and datasets "
    "in a benchmark-dedicated conda environment or in your own "
    "conda environment, see the command `benchopt install`."
)
@click.argument('benchmark', type=click.Path(exists=True),
                shell_complete=complete_benchmarks)
@click.option('--objective-filter',
              metavar='<objective_filter>', multiple=True, type=str,
              help="Deprecated alias for `--objective`.")
@click.option('--objective', '-o',
              metavar='<objective_filter>', multiple=True, type=str,
              help="Filter the objective based on its parametrized name. This "
              "can be used to only include one set of parameters.")
@click.option('--old-objective-filter', '-p',
              multiple=True, type=str,
              help="Deprecated alias for --objective_filter/-o.")
@click.option('--solver', '-s',
              metavar="<solver_name>", multiple=True, type=str,
              help="Include <solver_name> in the benchmark. By default, all "
              "solvers are included. When `-s` is used, only listed solvers"
              " are included. To include multiple solvers, "
              "use multiple `-s` options.", shell_complete=complete_solvers)
@click.option('--force-solver', '-f',
              metavar="<solver_name>", multiple=True, type=str,
              help="Force the re-run for <solver_name>. This "
              "avoids caching effect when adding a solver. "
              "To select multiple solvers, use multiple `-f` options.",
              shell_complete=complete_solvers)
@click.option('--dataset', '-d',
              metavar="<dataset_name>", multiple=True, type=str,
              help="Run the benchmark on <dataset_name>. By default, all "
              "datasets are included. When `-d` is used, only listed datasets"
              " are included. Note that <dataset_name> can be a regexp. "
              "To include multiple datasets, use multiple `-d` options.",
              shell_complete=complete_datasets)
@click.option('--n-jobs', '-j',
              metavar="<int>", default=1, show_default=True, type=int,
              help='Maximal number of workers to run the benchmark in '
              'parallel.')
@click.option('--max-runs', '-n',
              metavar="<int>", default=100, show_default=True, type=int,
              help='Maximal number of runs for each solver. This corresponds '
              'to the number of points in the time/accuracy curve.')
@click.option('--n-repetitions', '-r',
              metavar='<int>', default=5, show_default=True, type=int,
              help='Number of repetitions that are averaged to estimate the '
              'runtime.')
@click.option('--timeout',
              metavar="<int>", default=100, show_default=True, type=int,
              help='Timeout a solver when run for more than <timeout> seconds')
@click.option('--config', 'config_file', default=None,
              help="YAML configuration file containing benchmark options.")
@click.option('--plot/--no-plot', default=True,
              help="Whether or not to plot the results. Default is True.")
@click.option('--html/--no-html', default=True,
              help="Whether to display the plot as HTML report or matplotlib"
              "figures, default is True.")
@click.option('--pdb',
              is_flag=True,
              help="Launch a debugger if there is an error. This will launch "
              "ipdb if it is installed and default to pdb otherwise.")
@click.option('--local', '-l', 'env_name',
              flag_value='False', default=True,
              help="Run the benchmark in the local conda environment.")
@click.option('--profile',
              flag_value='True', default=False,
              help="Will do line profiling on all functions with @profile "
                   "decorator. Requires the line-profiler package. "
                   "The profile decorator needs to be imported "
                   "with: from benchopt.utils import profile")
@click.option('--env', '-e', 'env_name',
              flag_value='True',
              help="Run the benchmark in a dedicated conda environment "
              "for the benchmark. The environment is named "
              "benchopt_<BENCHMARK>.")
@click.option('--env-name', 'env_name',
              metavar="<env_name>", type=str, default='False',
              shell_complete=complete_conda_envs,
              help="Run the benchmark in the conda environment "
              "named <env_name>. To install the required solvers and "
              "datasets, see the command `benchopt install`.")
def run(config_file=None, **kwargs):
    if config_file is not None:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
    else:
        config = {}

    # XXX - Remove old and deprecated objective filters in version 1.3
    (
        benchmark, solver_names, forced_solvers, dataset_names,
        objective_filters, max_runs, n_repetitions, timeout, n_jobs,
        plot, html, pdb, do_profile, env_name, deprecated_objective_filters,
        old_objective_filters
    ) = _get_run_args(kwargs, config)

    if len(old_objective_filters):
        warnings.warn(
            'Using the -p option is deprecated, use -o instead',
            FutureWarning,
        )
        objective_filters = old_objective_filters

    if len(deprecated_objective_filters):
        warnings.warn(
            'Using the --objective-filters option is deprecated, '
            'use --objective instead', FutureWarning
        )
        objective_filters = deprecated_objective_filters

    from benchopt.runner import run_benchmark

    if do_profile:
        from benchopt.utils.profiling import use_profile
        use_profile()  # needs to be called before validate_solver_patterns

    # Check that the dataset/solver patterns match actual dataset
    benchmark = Benchmark(benchmark)
    benchmark.validate_dataset_patterns(dataset_names)
    benchmark.validate_objective_filters(objective_filters)
    # pyyaml returns tuples: solver_names can be tuple and forced_solvers list
    benchmark.validate_solver_patterns(
        list(solver_names) + list(forced_solvers)
    )

    # If env_name is False, the flag `--local` has been used (default) so
    # run in the current environment.
    if env_name == 'False':
        run_benchmark(
            benchmark, solver_names, forced_solvers,
            dataset_names=dataset_names,
            objective_filters=objective_filters,
            max_runs=max_runs, n_repetitions=n_repetitions,
            timeout=timeout, n_jobs=n_jobs,
            plot_result=plot, html=html, pdb=pdb
        )

        print_stats()  # print profiling stats (does nothing if not profiling)

        return

    _, all_conda_envs = list_conda_envs()
    # If env_name is True, the flag `--env` has been used. Create a conda env
    # specific to the benchmark (if not existing).
    # Else, use the <env_name> value.
    if env_name == 'True':
        env_name = f"benchopt_{benchmark.name}"
        install_cmd = f"`benchopt install -e {benchmark.benchmark_dir}`"
    else:
        # check provided <env_name>
        # (to avoid empty name like `--env-name ""`)
        if len(env_name) == 0:
            raise RuntimeError("Empty environment name.")

        install_cmd = (
            f"`benchopt install --env-name {env_name} "
            f"{benchmark.benchmark_dir}`"
        )

    # check if the environment exists
    if env_name not in all_conda_envs:
        raise RuntimeError(
            f"The default env '{env_name}' for benchmark {benchmark.name} "
            f"does not exist. Make sure to run {install_cmd} to create the "
            "benchmark and install the dependencies."
        )

    # check if environment was set up with benchopt
    if get_benchopt_version_in_env(env_name) is None:
        raise RuntimeError(
            f"benchopt is not installed in env '{env_name}', "
            "see the command `benchopt install` to setup the environment."
        )

    # run the command in the conda env
    solvers_option = ' '.join(['-s ' + s for s in solver_names])
    forced_solvers_option = ' '.join([f"-f '{s}'" for s in forced_solvers])
    datasets_option = ' '.join([f"-d '{d}'" for d in dataset_names])
    objective_option = ' '.join([f"-o '{o}'" for o in objective_filters])
    cmd = (
        rf"benchopt run --local {benchmark.benchmark_dir} "
        rf"--n-repetitions {n_repetitions} "
        rf"--max-runs {max_runs} --timeout {timeout} "
        rf"--n-jobs {n_jobs} "
        rf"{solvers_option} {forced_solvers_option} "
        rf"{datasets_option} {objective_option} "
        rf"{'--plot' if plot else '--no-plot'} "
        rf"{'--html' if html else '--no-html'} "
        rf"{'--pdb' if pdb else ''} "
        .replace('\\', '\\\\')
    )
    raise SystemExit(_run_shell_in_conda_env(
        cmd, env_name=env_name, capture_stdout=False
    ) != 0)


@main.command(
    help="Install the requirements (solvers/datasets) for a benchmark."
)
@click.argument('benchmark', type=click.Path(exists=True),
                shell_complete=complete_benchmarks)
@click.option('--force', '-f',
              is_flag=True,
              help="If this flag is set, the reinstallation of "
              "the benchmark requirements is forced.")
@click.option('--minimal', is_flag=True,
              help="If this flag is set, only install requirements for the "
              "benchmark's objective.")
@click.option('--solver', '-s', 'solver_names',
              metavar="<solver_name>", multiple=True, type=str,
              help="Include <solver_name> in the installation. "
              "By default, all solvers are included except "
              "when -d flag is used. If -d flag is used, then "
              "no solver is included by default. "
              "When `-s` is used, only listed estimators are included. "
              "To include multiple solvers, use multiple `-s` options."
              "To include all solvers, use -s 'all' option.",
              shell_complete=complete_solvers)
@click.option('--dataset', '-d', 'dataset_names',
              metavar="<dataset_name>", multiple=True, type=str,
              help="Install the dataset <dataset_name>. By default, all "
              "datasets are included, except when -s flag is used. "
              "If -s flag is used, then no dataset is included. "
              "When `-d` is used, only listed datasets "
              "are included. Note that <dataset_name> can be a regexp. "
              "To include multiple datasets, use multiple `-d` options."
              "To include all datasets, use -d 'all' option.",
              shell_complete=complete_datasets)
@click.option('--env', '-e', 'env_name',
              flag_value='True', type=str, default='False',
              help="Install all requirements in a dedicated "
              "conda environment for the benchmark. "
              "The environment is named 'benchopt_<BENCHMARK>' and all "
              "solver dependencies and datasets are installed in it.")
@click.option('--env-name', 'env_name',
              metavar="<env_name>", type=str, default='False',
              shell_complete=complete_conda_envs,
              help="Install the benchmark requirements in the "
              "conda environment named <env_name>. If it does not exist, "
              "it will be created by this command.")
@click.option('--recreate', is_flag=True,
              help="If this flag is set, start with a fresh conda "
              "environment. It can only be used combined with options "
              "`-e/--env` or `--env-name`.")
@click.option('--quiet', '-q', 'quiet', is_flag=True, default=False,
              show_default=True,
              help="If this flag is set, conda's output is silenced.")
@click.option('--yes', '-y', 'confirm', is_flag=True,
              help="If this flag is set, no confirmation will be asked "
              "to the user to install requirements in the current environment."
              " Useless with options `-e/--env` or `--env-name`.")
def install(benchmark, minimal, solver_names, dataset_names, force=False,
            recreate=False, env_name='False', confirm=False, quiet=False):

    # Check that the dataset/solver patterns match actual dataset
    benchmark = Benchmark(benchmark)
    print(f"Installing '{benchmark.name}' requirements")
    benchmark.validate_dataset_patterns(dataset_names)
    benchmark.validate_solver_patterns(solver_names)

    # Get a list of all conda envs
    default_conda_env, conda_envs = list_conda_envs()

    # If env_name is False (default), installation in the current environement.
    if env_name == 'False':
        env_name = None
        # incompatible with the 'recreate' flag to avoid messing with the
        # user environement
        if recreate:
            msg = "Cannot recreate conda env without using options " + \
                "'-e/--env' or '--env-name'."
            raise RuntimeError(msg)

        # check if any current conda environment
        if default_conda_env is not None:
            # ask for user confirmation to install in current conda env
            if not confirm:
                click.confirm(
                    f"Install in the current env '{default_conda_env}'?",
                    abort=True
                )
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
        create_conda_env(env_name, recreate=recreate, quiet=quiet)

    # install requirements
    print("# Install", flush=True)
    benchmark.install_all_requirements(
        include_solvers=solver_names, include_datasets=dataset_names,
        minimal=minimal, env_name=env_name, force=force, quiet=quiet,
    )


@main.command(
    help="Test a benchmark for benchopt. The benchmark must feature a "
    "simulated dataset to test for all solvers. For more info about the "
    "simulated dataset configurations, see"
    "benchopt.github.io/how.html#example-of-parametrized-simulated-dataset",
    context_settings=dict(ignore_unknown_options=True)
)
@click.argument('benchmark', type=click.Path(exists=True),
                shell_complete=complete_benchmarks)
@click.option('--env-name', type=str, default=None, metavar='NAME',
              shell_complete=complete_conda_envs,
              help='Environment to run the test in. If it is not provided '
              'a temporary one is created for the test.')
@click.argument('pytest_args', nargs=-1, type=click.UNPROCESSED)
def test(benchmark, env_name, pytest_args):

    benchmark = Benchmark(benchmark)

    from benchopt.tests import __file__ as _bench_test_module
    _bench_test_module = Path(_bench_test_module).parent

    pytest_args = ' '.join((
        "-p benchopt.tests.fixtures", f"--rootdir {_bench_test_module}",
        *pytest_args
    ))
    if len(pytest_args) == 0:
        pytest_args = '-vl'

    env_option = ''
    if env_name is not None:
        create_conda_env(env_name, with_pytest=True)
        if _run_shell_in_conda_env("pytest --version", env_name=env_name) != 0:
            raise ModuleNotFoundError(
                f"pytest is not installed in conda env {env_name}.\n"
                f"Please run `conda install -n {env_name} pytest` to test the "
                "benchmark in this environment."
            )
        objective = benchmark.get_benchmark_objective()
        if not objective.is_installed():
            objective.install(env_name=env_name)
        env_option = f'--test-env {env_name}'

    _bench_test_file = _bench_test_module / "test_benchmarks.py"

    cmd = (
        f'pytest {pytest_args} {_bench_test_file} '
        f'--benchmark {benchmark.benchmark_dir} {env_option} '
        # Make sure to not modify sys.path to add test file from current env
        # in sub conda env as there might be different python versions.
        '--import-mode importlib'
    )

    raise SystemExit(_run_shell_in_conda_env(
        cmd, env_name=env_name, capture_stdout=False
    ) != 0)
