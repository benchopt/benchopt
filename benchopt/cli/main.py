import click
from pathlib import Path

from benchopt.benchmark import Benchmark
from benchopt.cli.completion import get_solvers
from benchopt.cli.completion import get_datasets
from benchopt.cli.completion import get_benchmark
from benchopt.utils.shell_cmd import create_conda_env
from benchopt.utils.shell_cmd import _run_shell_in_conda_env, env_exists


main = click.Group(
    name='Principal Commands',
    help="Principal commands that are used in ``benchopt``."
)


@main.command(
    help="Run a benchmark with benchopt.",
    epilog="To (re-)install the required solvers and datasets "
    "in a benchmark-dedicated conda environment or in your own "
    "conda environment, see the command `benchopt install`."
)
@click.argument('benchmark', type=click.Path(exists=True),
                autocompletion=get_benchmark)
@click.option('--objective-filter', '-p', 'objective_filters',
              metavar='<objective_filter>', multiple=True, type=str,
              help="Filter the objective based on its parametrized name. This "
              "can be used to only include one set of parameters.")
@click.option('--solver', '-s', 'solver_names',
              metavar="<solver_name>", multiple=True, type=str,
              help="Include <solver_name> in the benchmark. By default, all "
              "solvers are included. When `-s` is used, only listed estimators"
              " are included. To include multiple solvers, "
              "use multiple `-s` options.", autocompletion=get_solvers)
@click.option('--force-solver', '-f', 'forced_solvers',
              metavar="<solver_name>", multiple=True, type=str,
              help="Force the re-run for <solver_name>. This "
              "avoids caching effect when adding an estimator."
              "To select multiple solvers, use multiple `-f` options.",
              autocompletion=get_solvers)
@click.option('--dataset', '-d', 'dataset_names',
              metavar="<dataset_name>", multiple=True, type=str,
              help="Run the benchmark on <dataset_name>. By default, all "
              "datasets are included. When `-d` is used, only listed datasets"
              " are included. Note that <dataset_name> can be a regexp. "
              "To include multiple datasets, use multiple `-d` options.",
              autocompletion=get_datasets)
@click.option('--max-runs', '-n',
              metavar="<int>", default=100, show_default=True, type=int,
              help='Maximal number of run for each solver. This corresponds '
              'to the number of points in the time/accuracy curve.')
@click.option('--n-repetitions', '-r',
              metavar='<int>', default=5, type=int,
              help='Number of repetition that are averaged to estimate the '
              'runtime.')
@click.option('--timeout',
              metavar="<int>", default=100, show_default=True, type=int,
              help='Timeout a solver when run for more than <timeout> seconds')
@click.option('--plot/--no-plot', default=True,
              help="Wether or not to plot the results. Default is True.")
@click.option('--pdb',
              is_flag=True,
              help="Launch a debugger if there is an error. This will launch "
              "ipdb if it is installed and default to pdb otherwise.")
@click.option('--local', '-l', 'env_name',
              flag_value='False', default=True,
              help="Run the benchmark in the local coinda environment."
              "To install the required solvers and datasets, "
              "see the command `benchopt install`.")
@click.option('--env', '-e', 'env_name',
              flag_value='True',
              help="Run the benchmark in a dedicated conda environment "
              "for the benchmark. The envenvironment is named "
              "benchopt_<BENCHMARK>.")
@click.option('--env-name', 'env_name',
              metavar="<env_name>", type=str, default='False',
              help="Run the benchmark in the conda environment "
              "named <env_name>."
              "To install the required solvers and datasets, "
              "see the command `benchopt install`.")
def run(benchmark, solver_names, forced_solvers, dataset_names,
        objective_filters, max_runs, n_repetitions, timeout,
        plot=True, pdb=False, env_name='False'):

    from benchopt.runner import run_benchmark

    # Check that the dataset/solver patterns match actual dataset
    benchmark = Benchmark(benchmark)
    benchmark.validate_dataset_patterns(dataset_names)
    benchmark.validate_solver_patterns(solver_names+forced_solvers)

    # If env_name is False, the flag `--local` has been used (default) so
    # run in the current environement.
    if env_name == 'False':
        run_benchmark(
            benchmark, solver_names, forced_solvers,
            dataset_names=dataset_names,
            objective_filters=objective_filters,
            max_runs=max_runs, n_repetitions=n_repetitions,
            timeout=timeout, plot_result=plot, pdb=pdb
        )
        return

    # If env_name is True, the flag `--env` has been used. Create a conda env
    # specific to the benchmark (if not existing).
    # Else, use the <env_name> value.
    if env_name == 'True':
        env_name = f"benchopt_{benchmark.name}"
        # create environment if necessary
        # (to avoid failure if `benchopt install -e` was not run)
        create_conda_env(env_name, recreate=False)
    else:
        # check provided <env_name>
        # (to avoid empty name like `--env-name ""`)
        if len(env_name) == 0:
            raise RuntimeError("Empty environment name.")

    # check if dedicated environment exists
    if not env_exists(env_name):
        msg = f"Environment '{env_name}' does not exist, " + \
            "see the command `benchopt install`?"
        raise RuntimeError(msg)

    # run the command in the conda env
    solvers_option = ' '.join(['-s ' + s for s in solver_names])
    forced_solvers_option = ' '.join(['-f ' + s for s in forced_solvers])
    datasets_option = ' '.join(['-d ' + d for d in dataset_names])
    objective_option = ' '.join(['-p ' + p for p in objective_filters])
    cmd = (
        rf"benchopt run --local {benchmark.benchmark_dir} "
        rf"--n-repetitions {n_repetitions} "
        rf"--max-runs {max_runs} --timeout {timeout} "
        rf"{solvers_option} {forced_solvers_option} "
        rf"{datasets_option} {objective_option} "
        rf"{'--plot' if plot else '--no-plot'} "
        rf"{'--pdb' if pdb else ''} "
        .replace('\\', '\\\\')
    )
    raise SystemExit(_run_shell_in_conda_env(
        cmd, env_name=env_name, capture_stdout=False
    ) != 0)


@main.command(
    help="Test a benchmark for benchopt.",
    context_settings=dict(ignore_unknown_options=True)
)
@click.argument('benchmark', type=click.Path(exists=True),
                autocompletion=get_benchmark)
@click.option('--env-name', type=str, default=None, metavar='NAME',
              help='Environment to run the test in. If it is not provided '
              'a temporary one is created for the test.')
@click.argument('pytest_args', nargs=-1, type=click.UNPROCESSED)
def test(benchmark, env_name, pytest_args):
    pytest_args = ' '.join(pytest_args)
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
        env_option = f'--test-env {env_name}'

    from benchopt.tests import __file__ as _bench_test_module
    BENCHMARK_TEST_FILE = (
        Path(_bench_test_module).parent / "test_benchmarks.py"
    )

    cmd = (
        f'pytest {pytest_args} {BENCHMARK_TEST_FILE} '
        f'--benchmark {benchmark} {env_option} '
        # Make sure to not modify sys.path to add test file from current env
        # in sub conda env as there might be different python versions.
        '--import-mode importlib'
    )

    raise SystemExit(_run_shell_in_conda_env(
        cmd, env_name=env_name, capture_stdout=False
    ) != 0)
