import click

from benchopt import run_benchmark


from benchopt.util import filter_solvers
from benchopt.util import get_all_benchmarks
from benchopt.util import install_required_datasets
from benchopt.util import _run_shell_in_env, create_conda_env
from benchopt.util import list_benchmark_solvers, install_solvers


from benchopt.config import get_benchmark_setting


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


def validate_benchmark(ctx, param, value):
    all_benchmarks = get_all_benchmarks()
    if not all_benchmarks:
        raise click.BadArgumentUsage(
            "benchopt should be run in a folder where there is benchmarks "
            "directory with at least one benchmark.")
    if value not in all_benchmarks:
        raise click.BadParameter(
            f"{value} is not a valid benchmark. "
            f"Should be one of: {all_benchmarks}"
        )
    return value


@click.group(context_settings=CONTEXT_SETTINGS)
def main(prog_name='benchopt'):
    """Command-line interface to benchOpt"""
    pass


@main.command()
@click.argument('benchmark', nargs=1, callback=validate_benchmark)
@click.option('--local', '-l',
              is_flag=True,
              help="If this flag is set, run the benchmark with the local "
              "interpreter.")
@click.option('--recreate', '-r',
              is_flag=True,
              help="If this flag is set, start with a fresh conda env.")
@click.option('--repetition', '-n',
              metavar='<int>', default=1, type=int,
              help='Number of repetition used to estimate the runtime.')
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
@click.option('--max-samples',
              metavar="<int>", default=100, show_default=True, type=int,
              help='Maximal number of iteration for each solver')
def run(benchmark, solver_names, forced_solvers, dataset_names,
        max_samples, recreate, local, repetition):
    """Run a benchmark in a separate venv where the solvers will be installed
    """

    if local:
        run_benchmark(benchmark, solver_names, forced_solvers, dataset_names,
                      max_samples=max_samples, n_rep=repetition)
        return

    create_conda_env(benchmark, recreate=recreate)

    # installed required datasets
    install_required_datasets(benchmark, dataset_names, env_name=benchmark)

    # Get the solvers and install them
    solvers = list_benchmark_solvers(benchmark)
    exclude = get_benchmark_setting(benchmark, 'exclude_solvers')
    solvers = filter_solvers(solvers, solver_names=solver_names,
                             forced_solvers=forced_solvers,
                             exclude=exclude)
    install_solvers(solvers=solvers, forced_solvers=forced_solvers,
                    env_name=benchmark)

    # run the command in the conda env
    solvers_option = ' '.join(['-s ' + s for s in solver_names])
    forced_solvers_option = ' '.join(['-f ' + s for s in forced_solvers])
    datasets_option = ' '.join(['-d ' + d for d in dataset_names])
    cmd = (
        f"benchopt run -l --max-samples {max_samples} -n {repetition} "
        f"{solvers_option} {forced_solvers_option} {datasets_option} "
        f"{benchmark}"
    )
    raise SystemExit(_run_shell_in_env(
        cmd, env_name=benchmark, capture_stdout=False))


def start():
    main()


if __name__ == '__main__':
    start()
