import click
import pandas as pd
from pathlib import Path

from benchopt import run_benchmark
from benchopt.viz import plot_benchmark

from benchopt.util import _load_class_from_module
from benchopt.util import install_required_solvers
from benchopt.util import install_required_datasets

from benchopt.utils.files import _get_output_folder
from benchopt.utils.checkers import validate_solver_patterns
from benchopt.utils.checkers import validate_dataset_patterns
from benchopt.utils.shell_cmd import _run_shell_in_conda_env, create_conda_env


BENCHMARK_TEST_FILE = Path(__file__).parent / 'tests' / 'test_benchmarks.py'


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
def main(prog_name='benchopt'):
    """Command-line interface to benchOpt"""
    pass


@main.command(
    help="Run a benchmark with benchopt."
)
@click.argument('benchmark', type=click.Path(exists=True))
@click.option('--local', '-l',
              is_flag=True,
              help="If this flag is set, run the benchmark with the local "
              "interpreter.")
@click.option('--recreate',
              is_flag=True,
              help="If this flag is set, start with a fresh conda env.")
@click.option('--objective-filter', '-p', 'objective_filters',
              metavar='<objective_filter>', multiple=True, type=str,
              help="Filter the objective based on its parametrized name. This "
              "can be used to only include one set of parameters.")
@click.option('--solver', '-s', 'solver_names',
              metavar="<solver_name>", multiple=True, type=str,
              help="Include <solver_name> in the benchmark. By default, all "
              "solvers are included. When `-s` is used, only listed estimators"
              " are included.")
@click.option('--force-solver', '-f', 'forced_solvers',
              metavar="<solver_name>", multiple=True, type=str,
              help="Force the re-installation and run for <solver_name>. This "
              "avoids caching effect when adding an estimator.")
@click.option('--dataset', '-d', 'dataset_names',
              metavar="<dataset_name>", multiple=True, type=str,
              help="Run the benchmark on <dataset_name>. By default, all "
              "datasets are included. When `-d` is used, only listed datasets"
              " are included. Note that <dataset_name> can be a regexp.")
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
@click.option('--no-plot',
              is_flag=True,
              help="If this flag is set, do not plot the results.")
def run(benchmark, solver_names, forced_solvers, dataset_names,
        objective_filters, max_runs, n_repetitions, timeout,
        recreate=False, local=True, no_plot=False):
    """Run a benchmark in a separate conda env where the deps will be installed
    """

    # Check that the dataset/solver patterns match actual dataset
    validate_dataset_patterns(benchmark, dataset_names)
    validate_solver_patterns(benchmark, solver_names+forced_solvers)

    if local:
        run_benchmark(
            benchmark, solver_names, forced_solvers,
            dataset_names=dataset_names, objective_filters=objective_filters,
            max_runs=max_runs, n_repetitions=n_repetitions, timeout=timeout,
            plot_result=not no_plot
        )
        return

    benchmark_name = Path(benchmark).name
    env_name = f"benchopt_{benchmark_name}"
    create_conda_env(env_name, recreate=recreate)

    # installed required datasets
    install_required_datasets(benchmark, dataset_names, env_name=env_name)

    # Get the solvers and install them
    install_required_solvers(
        benchmark, solver_names, forced_solvers=forced_solvers,
        env_name=env_name
    )

    # run the command in the conda env
    solvers_option = ' '.join(['-s ' + s for s in solver_names])
    forced_solvers_option = ' '.join(['-f ' + s for s in forced_solvers])
    datasets_option = ' '.join(['-d ' + d for d in dataset_names])
    objective_option = ' '.join(['-p ' + p for p in objective_filters])
    cmd = (
        f"benchopt run {benchmark} --local --n-repetitions {n_repetitions} "
        f"--max-runs {max_runs} --timeout {timeout} "
        f"{solvers_option} {forced_solvers_option} "
        f"{datasets_option} {objective_option} "
        f"{'--no-plot' if no_plot else ''} "
    )
    raise SystemExit(_run_shell_in_conda_env(
        cmd, env_name=env_name, capture_stdout=False
    ) != 0)


@main.command(
    help="Plot the result from a previously run benchmark."
)
@click.argument('benchmark', type=click.Path(exists=True))
@click.option('--filename', '-f',
              type=str, default=None,
              help="Specify the file to select in the benchmark. If it is "
              "not specified, take the latest on in the benchmark output "
              "folder.")
@click.option('--kind', '-k', 'kinds',
              multiple=True, show_default=True, type=str,
              help='Timeout a solver when run for more than <timeout> seconds')
@click.option('--no-display',
              is_flag=True,
              help="If this flag is set, do not display the plot on the "
              "screen.")
def plot(benchmark, filename=None, kinds=('convergence_curve',),
         no_display=False):

    output_folder = _get_output_folder(benchmark)
    all_csv_files = output_folder.glob("*.csv")
    all_csv_files = sorted(
        all_csv_files, key=lambda t: t.stat().st_mtime
    )
    if filename is not None:
        if (output_folder / filename).exists():
            result_filename = output_folder / filename
        elif Path(filename).exists():
            result_filename = Path(filename)
        else:
            all_csv_files = '\n- '.join([str(s) for s in all_csv_files])
            raise FileNotFoundError(
                f"Could not find result file {filename}. Available result "
                f"files are:\n- {all_csv_files}"
            )
    else:
        result_filename = all_csv_files[-1]

    df = pd.read_csv(result_filename)
    plot_benchmark(df, benchmark, kinds=kinds, display=not no_display)


@main.command(
    help="Check that a given solver or dataset is correctly installed.\n\n"
    "The class to be checked is specified with the absolute path of the file "
    "in which it is defined MODULE_FILENAME and the name of the base "
    "class BASE_CLASS_NAME."
)
@click.argument('module_filename', nargs=1, type=Path)
@click.argument('base_class_name', nargs=1, type=str)
def check_install(module_filename, base_class_name):

    # Get class to check
    klass = _load_class_from_module(module_filename, base_class_name)
    klass.is_installed(raise_on_not_installed=True)


@main.command(
    help="Test a benchmark in BENCHMARK_DIR.",
    context_settings=dict(ignore_unknown_options=True)
)
@click.argument('benchmark_dir', type=click.Path(exists=True))
@click.option('--env-name', type=str, default=None, metavar='NAME',
              help='Environment to run the test in. If it is not provided '
              'a temporary one is created for the test.')
@click.argument('pytest_args', nargs=-1, type=click.UNPROCESSED)
def test(benchmark_dir, env_name, pytest_args):
    pytest_args = ' '.join(pytest_args)
    if len(pytest_args) == 0:
        pytest_args = '-vl'

    env_option = ''
    if env_name is not None:
        create_conda_env(env_name, with_pytest=True)
        env_option = f'--test-env {env_name}'
    cmd = (
        f'pytest {pytest_args} {BENCHMARK_TEST_FILE} '
        f'--benchmark {benchmark_dir} {env_option}'
    )

    raise SystemExit(_run_shell_in_conda_env(
        cmd, env_name=env_name, capture_stdout=False
    ) != 0)


if __name__ == '__main__':
    main()
