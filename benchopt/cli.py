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


@main.command()
@click.option('--bench', default='all', show_default=True,
              help='Select a benchmark to run by its name')
@click.option('--max-iter', default=1000, show_default=True,
              help='Maximal number of iteration for each solver')
def run(bench, max_iter):
    """Run benchmark."""

    if bench == 'all':
        bench = get_all_benchmarks()
    elif isinstance(bench, str):
        bench = [bench]

    for b in bench:
        run_benchmark(b, max_iter=max_iter)


@main.command()
@click.argument('benchmark', nargs=-1)
@click.option('--max-iter', default=1000, show_default=True,
              help='Maximal number of iteration for each solver')
def bench(benchmark, max_iter):
    """Run benchmark."""

    if benchmark == ():
        benchmarks = get_all_benchmarks()

    for benchmark in benchmarks:
        # Run the benchmark in a separate venv where the solvers
        # will be installed
        run_benchmark_in_venv(benchmark, max_iter=max_iter)


def start():
    main()


if __name__ == '__main__':
    start()
