import sys
import click

from benchopt import __version__

from benchopt.cli.main import main
from benchopt.cli.helpers import helpers
from benchopt.cli.process_results import process_results

from benchopt.utils.misc import get_benchopt_requirement


SOURCES = [main, process_results, helpers]
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.command(name='benchopt', cls=click.CommandCollection, sources=SOURCES,
               context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option('--version', '-v', is_flag=True, help='Print version')
@click.option('--check-env', is_flag=True,
              help='Output more info for version checking, and format as: '
              'BENCHOPT_VERSION:<version>:<is_editable>.')
@click.pass_context
def benchopt(ctx, version=False, check_env=False):
    """Command line interface to benchopt"""
    if version:
        output = __version__
        print(output)
        raise SystemExit(0)
    if check_env:
        _, is_editable = get_benchopt_requirement()
        try:
            from pytest import __version__ as pytest_version
        except ImportError:
            pytest_version = None
        output = {
            'version': __version__,
            'is_editable': is_editable,
            'python_version': sys.version.split()[0],
            'pytest_version': pytest_version
        }
        import json
        json.dump(output, sys.stdout)
        raise SystemExit(0)
    if ctx.invoked_subcommand is None:
        print(benchopt.get_help(ctx))


if __name__ == '__main__':
    benchopt()
