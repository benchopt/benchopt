import click
from glob import glob

from benchopt import run_benchmark

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
def main():
    """Command-line interface to benchOpt"""
    pass


def get_all_benchmarks():
    benchmark_files = glob("benchmarks/*/bench_*.py")
    return [b.replace('.py', '').replace('/', '.')
            for b in benchmark_files]


@main.command()
@click.option('--bench', default='all', show_default=True,
              help='Select a benchmark to run by its name')
def run(bench):
    """Run benchmark."""

    if bench == 'all':
        bench = get_all_benchmarks()
    elif isinstance(bench, str):
        bench = [bench]

    for b in bench:
        run_benchmark(b)


def start():
    main()


if __name__ == '__main__':
    start()
