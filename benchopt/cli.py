import re
import click
from glob import glob

from benchopt import run_benchmark
from benchopt import run_benchmark_in_venv

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
def main():
    """Command-line interface to benchOpt"""
    pass


def get_all_benchmarks():
    benchmark_files = glob("benchmarks/*/bench*.py")
    benchmarks = []
    for benchmark_file in benchmark_files:
        match = re.match(r"benchmarks/([^/]*)/*", benchmark_file)
        benchmarks.append(match.groups()[0])
    return benchmarks


def check_benchmarks(benchmarks, all_benchmarks):
    unknown_benchmarks = set(benchmarks) - set(all_benchmarks)
    assert len(unknown_benchmarks) == 0, (
        "{} is not a valid benchmark. Should be one of: {}"
        .format(unknown_benchmarks, all_benchmarks)
    )


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
    # check_solvers(benc)

    for b in benchmarks:
        run_benchmark(b, max_iter=max_iter)


@main.command()
@click.argument('benchmarks', nargs=-1)
@click.option('--max-iter', default=1000, show_default=True, type=int,
              help='Maximal number of iteration for each solver')
def bench(benchmarks, max_iter):
    """Run benchmark."""

    all_benchmarks = get_all_benchmarks()
    if benchmarks == ():
        benchmarks = all_benchmarks

    check_benchmarks(benchmarks, all_benchmarks)

    return_code = {}
    for benchmark in benchmarks:
        # Run the benchmark in a separate venv where the solvers
        # will be installed
        ret_code = run_benchmark_in_venv(benchmark, max_iter=max_iter)
        return_code[benchmark] = ret_code


def start():
    main()


if __name__ == '__main__':
    start()
