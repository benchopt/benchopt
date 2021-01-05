import click

from benchopt import __version__

from benchopt.cli.main import main
from benchopt.cli.helpers import helpers
from benchopt.cli.process_results import process_results


SOURCES = [main, process_results, helpers]
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.command(name='benchopt', cls=click.CommandCollection, sources=SOURCES,
               context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option('--version', '-v', is_flag=True, help='Print version')
@click.pass_context
def benchopt(ctx, version=False):
    """Command-line interface to benchOpt"""
    if version:
        print(__version__)
        raise SystemExit(0)
    if ctx.invoked_subcommand is None:
        print(benchopt.get_help(ctx))


if __name__ == '__main__':
    benchopt()
