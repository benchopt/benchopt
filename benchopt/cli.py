import click

from benchopt import run_benchmark


from benchopt.util import filter_solvers
from benchopt.util import get_all_benchmarks
from benchopt.util import _run_bash_in_env, create_venv
from benchopt.util import list_benchmark_solvers, install_solvers


from benchopt.config import get_benchmark_setting


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


def validate_benchmark(ctx, param, value):
    all_benchmarks = get_all_benchmarks()
    if value not in all_benchmarks:
        raise click.BadParameter(
            f"{value} is not a valid benchmark. "
            f"Should be one of: {all_benchmarks}"
        )
    return value


@click.group(context_settings=CONTEXT_SETTINGS)
def main():
    """Command-line interface to benchOpt"""
    pass


@main.command()
@click.argument('benchmark', nargs=1, callback=validate_benchmark)
@click.option('--repetition', '-n',
              metavar='<int>', default=1, type=int,
              help='Number of repetition used to estimate the runtime.')
@click.option('--solver', '-s', 'solver_names',
              metavar="<solver_name>", multiple=True, type=str,
              help='Include solver_names in the benchmark')
@click.option('--force-solver', '-f', 'forced_solvers',
              metavar="<solver_name>", multiple=True, type=str,
              help="Force the run for <solver_name>, evn if it is already "
              "cached.")
@click.option('--max-samples',
              metavar="<int>", default=100, show_default=True, type=int,
              help='Maximal number of iteration for each solver')
def run(benchmark, solver_names, forced_solvers, max_samples, repetition):
    """Run a benchmark"""
    run_benchmark(benchmark, solver_names, forced_solvers,
                  max_samples=max_samples, n_rep=repetition)


@main.command()
@click.argument('benchmark', nargs=1, callback=validate_benchmark)
@click.option('--recreate', '-r',
              is_flag=True,
              help="If this flag is set, start with a fresh venv.")
@click.option('--repetition', '-n',
              metavar='<int>', default=1, type=int,
              help='Number of repetition used to estimate the runtime.')
@click.option('--solver', '-s', 'solver_names', multiple=True, type=str)
@click.option('--force-solver', '-f', 'forced_solvers',
              metavar="<solver_name>", multiple=True, type=str,
              help="Force the run for <solver_name>, evn if it is already "
              "cached.")
@click.option('--max-samples',
              metavar="<int>", default=100, show_default=True, type=int,
              help='Maximal number of iteration for each solver')
def bench(benchmark, solver_names, forced_solvers, max_samples, recreate,
          repetition):
    """Run a benchmark in a separate venv where the solvers will be installed
    """

    # Create the virtual env
    create_venv(benchmark, recreate=recreate)

    # Get the solvers and install them
    solvers = list_benchmark_solvers(benchmark)
    exclude = get_benchmark_setting(benchmark, 'exclude_solvers')
    solvers = filter_solvers(solvers, solver_names=solver_names,
                             forced_solvers=forced_solvers,
                             exclude=exclude)
    install_solvers(solvers=solvers, forced_solvers=forced_solvers,
                    env_name=benchmark)

    solvers_option = ' '.join(['-s '+s for s in solver_names])
    forced_solvers_option = ' '.join(['-f '+s for s in forced_solvers])
    cmd = (
        f"benchopt run --max-samples {max_samples} -n {repetition} "
        f"{solvers_option} {forced_solvers_option} {benchmark}"
    )
    exit_code = _run_bash_in_env(cmd, env_name=benchmark,
                                 capture_stdout=False)
    raise SystemExit(exit_code)


def start():
    main()


if __name__ == '__main__':
    start()
