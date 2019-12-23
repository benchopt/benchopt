import click

from benchopt import run_benchmark


from benchopt.util import _run_bash_in_env, create_venv
from benchopt.util import check_benchmarks, get_all_benchmarks
from benchopt.util import get_all_solvers, install_solvers


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
def main():
    """Command-line interface to benchOpt"""
    pass


@main.command()
@click.argument('benchmarks', nargs=-1)
@click.option('--solver', '-s', multiple=True, type=str)
@click.option('--max-iter', default=1000, show_default=True, type=int,
              help='Maximal number of iteration for each solver')
def run(benchmarks, solver, max_iter):
    """Run benchmark."""

    all_benchmarks = get_all_benchmarks()
    if benchmarks == 'all':
        benchmarks = all_benchmarks

    check_benchmarks(benchmarks, all_benchmarks)

    # TODO: check solvers
    solver_names = None if solver == () else list(s.lower() for s in solver)
    # check_solvers(benchmarks)

    for benchmark in benchmarks:
        run_benchmark(benchmark, solver_names, max_iter=max_iter)


@main.command()
@click.argument('benchmarks', nargs=-1)
@click.option('--solver', '-s', 'solver_names', multiple=True, type=str)
@click.option('--max-iter', default=1000, show_default=True, type=int,
              help='Maximal number of iteration for each solver')
@click.option('--recreate', '-r', is_flag=True)
def bench(benchmarks, solver_names, max_iter, recreate):
    """Run benchmark."""

    all_benchmarks = get_all_benchmarks()
    if benchmarks == ():
        benchmarks = all_benchmarks

    check_benchmarks(benchmarks, all_benchmarks)

    return_code = {}
    for benchmark in benchmarks:
        # Run the benchmark in a separate venv where the solvers
        # will be installed

        # Create the virtual env
        create_venv(benchmark, recreate=recreate)

        # Get the solvers and install them
        solvers = get_all_solvers(benchmark)
        solvers = [solver for solver in solvers
                   if solver.name.lower() in solver_names]
        install_solvers(solvers=solvers, env_name=benchmark)

        solvers_option = ' '.join(['-s '+s for s in solver_names])
        cmd = (
            f"benchopt run --max-iter {max_iter} {solvers_option} {benchmark}"
        )
        exit_code = _run_bash_in_env(cmd, env_name=benchmark)
        return_code[benchmark] = exit_code


def start():
    main()


if __name__ == '__main__':
    start()
