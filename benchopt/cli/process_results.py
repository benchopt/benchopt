import click
import warnings
from pathlib import Path

from benchopt.config import get_setting
from benchopt.benchmark import Benchmark
from benchopt.results import save_results
from benchopt.cli.completion import complete_benchmarks
from benchopt.cli.completion import complete_output_files
from benchopt.cli.completion import complete_plots

process_results = click.Group(
    name='Process results',
    help="Utilities to process benchmark outputs produced by benchopt."
)


@process_results.command(
    help="Plot the result from a previously run benchmark."
)
@click.argument('benchmark', default=Path.cwd(), type=click.Path(exists=True),
                shell_complete=complete_benchmarks)
@click.option('--filename', '-f', type=str, default=None,
              shell_complete=complete_output_files,
              help="Specify the file to select in the benchmark. If it is "
              "not specified, take the latest one in the benchmark output "
              "folder.")
@click.option('--kind', '-k', 'kinds',
              multiple=True, show_default=True, type=str,
              shell_complete=complete_plots,
              help="Specify the type of figure to plot")
@click.option('--display/--no-display', default=True,
              help="Whether or not to display the plot on the screen. "
              "Default is True.")
@click.option('--html/--no-html', default=True,
              help="If set to True (default), render the results as an HTML "
              "page, otherwise create matplotlib figures, saved as PNG.")
@click.option('--plotly', is_flag=True,
              help="If this flag is set, generate figure as HTML with plotly. "
              "This option does not work with all plot kinds and requires "
              "to have installed `plotly`.")
@click.option('--all', 'all_files', is_flag=True,
              help="If this flag is set, generate the plot for all existing "
              "runs of a benchmark at once.")
def plot(benchmark, filename=None, kinds=('suboptimality_curve',),
         display=True, html=True, plotly=False, all_files=False):

    if all_files:
        assert filename is None, (
            "Cannot use `--all` and `--filename` simultaneously."
        )
        assert html, '`--all` can only be used for HTML plot generation.'
        filename = 'all'

    if html and len(kinds) > 0:
        warnings.warn("Cannot specify '--kind' for HTML plot, this options "
                      "will be ignored.")

    # Get the result file
    benchmark = Benchmark(benchmark)
    result_filename = benchmark.get_result_file(filename)

    # Plot the results.
    from benchopt.plotting import plot_benchmark
    plot_benchmark(result_filename, benchmark, kinds=kinds, display=display,
                   plotly=plotly, html=html)


@process_results.command(
    help="Merge multiple result files from a benchmark."
)
@click.argument('benchmark', default=None, type=click.Path(exists=True),
                required=False, shell_complete=complete_benchmarks)
@click.option('--filenames', '-f', type=str, multiple=True,
              shell_complete=complete_output_files,
              help="Specify the files to merge in the benchmark. If it is "
              "not specified, take all files in the benchmark output folder.")
@click.option('--overwrite', is_flag=True,
              help="If this flag is set, when merging files, consider that "
              "they can contain multiple times the same configuration, and only "
              "keep the last one. This is useful when merging files from "
              "multiple runs where we add new methods but don't want to lose "
              "the results of the already existing methods.")
@click.option('--output', '-o', type=str, default="merged_results.parquet",
              help="Specify the name of the output file. If not specified, "
              "the merged results will be saved in a file named "
              "`merged_results.parquet` in the benchmark output folder.")
def merge(benchmark, filenames=None, overwrite=False, output=None):

    if len(filenames) == 0:
        filenames = "all"

    # Get the result files
    if benchmark is None and (Path() / "objective.py").exists():
        benchmark = Path()
    if benchmark is not None:
        benchmark = Benchmark(benchmark)
        result_filenames = benchmark.get_result_file(filenames)
    else:
        result_filenames = [Path(f) for f in filenames]

    if benchmark is not None:
        output = benchmark.get_output_folder() / output
    else:
        output = Path(output)

    # Merge the results.
    from benchopt.results.process import merge_results
    df = merge_results(result_filenames, overwrite=overwrite)
    save_results(df, output)


@process_results.command(
    help="Publish the result from a previously run benchmark.\n\n"
    "See the :ref:`publish_benchmark` documentation for more info on how "
    "to use this command."
)
@click.argument('benchmark', default=Path.cwd(), type=click.Path(exists=True),
                shell_complete=complete_benchmarks)
@click.option('--token', '-t', type=str, default=None,
              help="Github token to access the result repo.")
@click.option('--filename', '-f', type=str, default=None,
              shell_complete=complete_output_files,
              help="Specify the file to publish in the benchmark. If it is "
              "not specified, take the latest one in the benchmark output "
              "folder.")
def publish(benchmark, token=None, filename=None):

    if token is None:
        token = get_setting('github_token')
    if token is None:
        raise RuntimeError(
            "Could not find the token value to connect to GitHub.\n\n"
            "Please go to https://github.com/settings/tokens to generate a "
            "personal token $TOKEN.\nThen, either provide it with option `-t` "
            "or put it in a config file ./benchopt.yml\nunder section "
            "[benchopt] as `github_token = $TOKEN`."
        )

    # Get the result file
    benchmark = Benchmark(benchmark)
    result_filename = benchmark.get_result_file(filename)

    # Publish the result.
    from benchopt.utils.github import publish_result_file
    publish_result_file(benchmark, result_filename, token)


@process_results.command(
    help="Generate result website from list of benchmarks."
)
@click.option('--benchmark', '-b', 'benchmark_paths', metavar="<bench>",
              multiple=True,
              type=click.Path(exists=True),
              shell_complete=complete_benchmarks,
              help="Folders containing benchmarks to include.")
@click.option('--pattern', '-k', 'patterns',
              metavar="<pattern>", multiple=True, type=str,
              help="Include results matching <pattern>.")
@click.option('--root', 'root', metavar="<root>",
              type=click.Path(exists=True), default=Path.cwd(),
              help="If no benchmark is provided, include all benchmark in "
              "sub-directories of <root>. Default to current dir.")
@click.option('--display/--no-display', default=True,
              help="Whether or not to display the plot on the screen.")
def generate_results(patterns=(), benchmark_paths=(), root=None, display=True):
    from benchopt.plotting.generate_html import plot_benchmark_html_all
    plot_benchmark_html_all(
        patterns=patterns, benchmark_paths=benchmark_paths,
        root=root, display=display
    )
