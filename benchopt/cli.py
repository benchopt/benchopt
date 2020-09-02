import click
from pathlib import Path

from benchopt import run_benchmark


from benchopt.util import filter_classes_on_name
from benchopt.util import _load_class_from_module
from benchopt.util import install_required_datasets
from benchopt.util import list_benchmark_solvers, install_solvers

from benchopt.utils.checkers import validate_solver_patterns
from benchopt.utils.checkers import validate_dataset_patterns
from benchopt.utils.shell_cmd import _run_shell_in_conda_env, create_conda_env


from benchopt.config import get_benchmark_setting


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
@click.option('--n-repetitions', '-r',
              metavar='<int>', default=5, type=int,
              help='Number of repetition that are averaged to estimate the '
              'runtime.')
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
@click.option('--timeout',
              metavar="<int>", default=100, show_default=True, type=int,
              help='Timeout a solver when run for more than <timeout> seconds')
def run(benchmark, solver_names, forced_solvers, dataset_names,
        max_runs, n_repetitions, timeout, recreate, local):
    """Run a benchmark in a separate venv where the solvers will be installed
    """

    # Check that the dataset/solver patterns match actual dataset
    validate_dataset_patterns(benchmark, dataset_names)
    validate_solver_patterns(benchmark, solver_names+forced_solvers)

    if local:
        run_benchmark(benchmark, solver_names, forced_solvers, dataset_names,
                      max_runs=max_runs, n_repetitions=n_repetitions,
                      timeout=timeout)
        return

    benchmark_name = Path(benchmark).name
    env_name = f"benchopt_{benchmark_name}"
    create_conda_env(env_name, recreate=recreate)

    # installed required datasets
    install_required_datasets(benchmark, dataset_names, env_name=env_name)

    # Get the solvers and install them
    solvers = list_benchmark_solvers(benchmark)
    exclude = get_benchmark_setting(benchmark, 'exclude_solvers')
    solvers = filter_classes_on_name(
        solvers, include=solver_names, forced=forced_solvers, exclude=exclude
    )
    install_solvers(solvers=solvers, forced_solvers=forced_solvers,
                    env_name=env_name)

    # run the command in the conda env
    solvers_option = ' '.join(['-s ' + s for s in solver_names])
    forced_solvers_option = ' '.join(['-f ' + s for s in forced_solvers])
    datasets_option = ' '.join(['-d ' + d for d in dataset_names])
    cmd = (
        f"benchopt run {benchmark} --local --n-repetitions {n_repetitions} "
        f"--max-runs {max_runs} --timeout {timeout} "
        f"{solvers_option} {forced_solvers_option} {datasets_option} "
        f""
    )
    raise SystemExit(_run_shell_in_conda_env(
        cmd, env_name=env_name, capture_stdout=False
    ))


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


if __name__ == '__main__':
    main()
