import click
import pandas as pd

from benchopt.config import get_setting
from benchopt.benchmark import Benchmark
from benchopt.plotting import PLOT_KINDS
from benchopt.plotting import plot_benchmark
from benchopt.utils.github import publish_result_file


process_results = click.Group(
    name='Process Results',
    help="Utilities to process benchmark outputs produced by benchOpt."
)


def get_plot_kinds(ctx, args, incomplete):
    kinds = list(PLOT_KINDS)
    return [k for k in kinds if incomplete in k]


@process_results.command(
    help="Plot the result from a previously run benchmark."
)
@click.argument('benchmark', type=click.Path(exists=True))
@click.option('--filename', '-f', type=str, default=None,
              help="Specify the file to select in the benchmark. If it is "
              "not specified, take the latest on in the benchmark output "
              "folder.")
@click.option('--kind', '-k', 'kinds',
              multiple=True, show_default=True, type=str,
              help="Specify the type of figure to plot:\n\n* " +
              "\n\n* ".join([f"``{name}``: {func.__doc__.splitlines()[0]}"
                             for name, func in PLOT_KINDS.items()]),
              autocompletion=get_plot_kinds)
@click.option('--display/--no-display', default=True,
              help="Whether or not to display the plot on the screen.")
@click.option('--plotly', is_flag=True,
              help="If this flag is set, generate figure as HTML with plotly. "
              "This option does not work with all plot kinds and requires "
              "to have installed `plotly`.")
def plot(benchmark, filename=None, kinds=('suboptimality_curve',),
         display=True, plotly=False):

    # Get the result file
    benchmark = Benchmark(benchmark)
    result_filename = benchmark.get_result_file(filename)

    # Plot the results.
    df = pd.read_csv(result_filename)
    plot_benchmark(df, benchmark, kinds=kinds, display=display, plotly=plotly)


@process_results.command(
    help="Publish the result from a previously run benchmark.\n\n"
    "See the :ref:`publish_doc` documentation for more info on how to use "
    "this command."
)
@click.argument('benchmark', type=click.Path(exists=True))
@click.option('--token', '-t', type=str, default=None,
              help="Github token to access the result repo.")
@click.option('--filename', '-f',
              type=str, default=None,
              help="Specify the file to publish in the benchmark. If it is "
              "not specified, take the latest on in the benchmark output "
              "folder.")
def publish(benchmark, token=None, filename=None):

    if token is None:
        token = get_setting('github_token')
    if token is None:
        raise RuntimeError(
            "Could not find the token value to connect to GitHub.\n\n"
            "Please go to https://github.com/settings/tokens to generate a "
            "personal token $TOKEN.\nThen, either provide it with option `-t` "
            "or put it in a config file ./benchopt.ini\nunder section "
            "[benchopt] as `github_token = $TOKEN`."
        )

    # Get the result file
    benchmark = Benchmark(benchmark)
    result_filename = benchmark.get_result_file(filename)

    # Publish the result.
    publish_result_file(benchmark.name, result_filename, token)
