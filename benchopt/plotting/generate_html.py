import glob
import shutil
import webbrowser
from pathlib import Path
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
from mako.template import Template

from ..constants import PLOT_KINDS
from .plot_histogram import plot_histogram  # noqa: F401
from .plot_objective_curve import plot_objective_curve  # noqa: F401
from .plot_objective_curve import plot_suboptimality_curve  # noqa: F401
from .plot_objective_curve import plot_relative_suboptimality_curve  # noqa: F401 E501


ROOT = Path(__file__).parent / "html"
HTML_DIR = Path("html")
HTML_DIR_OUTPUTS = HTML_DIR / "outputs"
HTML_DIR_FIGURES = HTML_DIR / "figures"

TEMPLATE_INDEX = ROOT / "templates" / "index.mako.html"
TEMPLATE_BENCHMARK = ROOT / "templates" / "benchmark.mako.html"
TEMPLATE_RESULT = ROOT / "templates" / "result.mako.html"
TEMPLATE_LOCAL_RESULT = ROOT / "templates" / "local_result.mako.html"


def generate_plot_benchmark(df, kinds, fname):
    """Generate all possible plots for a given benchmark run.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.
    kinds : list of str
        List of the kind of plots that will be generated. This needs to be a
        sub-list of PLOT_KINDS.keys().
    fname: str
        HTML file name.

    Returns
    -------
    dict
        The figures for convergence curves and histograms
        for each dataset.
    """
    dataset_names = df['data_name'].unique()
    objective_names = df['objective_name'].unique()
    fname_short = fname.replace('outputs/', '').replace('/', '_')

    figures = {}
    n_figure = 0
    for data_name in dataset_names:
        figures[data_name] = {}
        df_data = df[df['data_name'] == data_name]
        for objective_name in objective_names:
            figures[data_name][objective_name] = {}
            df_obj = df_data[df_data['objective_name'] == objective_name]

            for k in kinds:
                if k not in PLOT_KINDS:
                    raise ValueError(
                        f"Requesting invalid plot '{k}'. Should be in:\n"
                        f"{PLOT_KINDS}")
                plot_func = globals()[PLOT_KINDS[k]]
                try:
                    fig = plot_func(df_obj, plotly=True)
                except TypeError:
                    fig = plot_func(df_obj)
                figures[data_name][objective_name][k] = export_figure(
                    fig, f"{fname_short}_{n_figure}"
                )
                n_figure += 1

    return dict(
        figures=figures, dataset_names=dataset_names, fname_short=fname_short,
        objective_names=objective_names, kinds=list(kinds)
    )


def export_figure(fig, fig_name):
    """
    Export figure to HTML or svg.

    Parameters
    ----------
    fig : plotly.graph_objs.Figure
        Figure from plotly

    fig_name : str
        Name to be given to the figure.

    Returns
    -------
    str
        Path to the figure.
    """
    if hasattr(fig, 'to_html'):
        return fig.to_html(include_plotlyjs=False)

    fig_basename = f"{fig_name}.svg"
    save_name = HTML_DIR_FIGURES / fig_basename
    fig.savefig(save_name)
    plt.close(fig)
    return f'figures/{fig_basename}'


def get_result_from_df(df, kinds):
    """
    Generate figure and CSV file from dataframe

    Parameters
    ----------
    df : pandas.DataFrame
        pandas DataFrame containing the benchmark results
    kinds : list of str
        List of the kind of plots that will be generated. This needs to be a
        sub-list of PLOT_KINDS.keys().

    Returns
    -------
    dict
        Dictionary containing to results
    """
    results = []
    HTML_DIR_OUTPUTS.mkdir(exist_ok=True, parents=True)
    HTML_DIR_FIGURES.mkdir(exist_ok=True, parents=True)

    datasets = list(df['data_name'].unique())
    fname = "benchmark_benchopt_run_" + str(datetime.now())[:19] + ".csv"
    fname = fname.replace(" ", "_").replace(":", "_")

    # Generate figures
    result = dict(
        fname=fname,
        datasets=datasets,
        **generate_plot_benchmark(df, kinds, fname)
    )
    result['page'] = f"{str(result['fname_short']).replace('.csv', '.html')}"
    results.append(result)

    return results


def get_results(fnames, kinds, copy=False):
    """
    Generate figures and CSV files from several dataframes

    Parameters
    ----------
    fnames : list of str
        list of csv files containing the benchmark results
    kinds : list of str
        List of the kind of plots that will be generated. This needs to be a
        sub-list of PLOT_KINDS.keys().

    Returns
    -------
    dict
        Dictionary containing to results
    """
    results = []
    HTML_DIR_OUTPUTS.mkdir(exist_ok=True, parents=True)
    HTML_DIR_FIGURES.mkdir(exist_ok=True, parents=True)

    for fname in fnames:
        print(f"Processing {fname}")

        df = pd.read_csv(fname)
        datasets = list(df['data_name'].unique())

        # Copy CSV
        if copy:
            fname_no_output = fname.replace('outputs/', '')
            fname_no_output_path = Path(fname_no_output)
            shutil.copy(fname, HTML_DIR_OUTPUTS / fname_no_output_path)

        # Generate figures
        result = dict(
            fname=fname,
            datasets=datasets,
            **generate_plot_benchmark(df, kinds, fname)
        )
        results.append(result)

    for result in results:
        result['page'] = \
            f"{str(result['fname_short']).replace('.csv', '.html')}"

    return results


def render_benchmark(results, benchmark):
    """ Render HTML pages with all plots for 1 run of the benchmark. """
    return Template(filename=str(TEMPLATE_BENCHMARK),
                    input_encoding="utf-8").render(
        results=results,
        benchmark=benchmark,
        max_rows=15,
        nb_total_benchs=len(results),
        last_updated=datetime.now(),
    )


def render_index(benchmarks):
    """ Render the benchmark's home page to index all runs. """
    return Template(filename=str(TEMPLATE_INDEX),
                    input_encoding="utf-8").render(
        benchmarks=benchmarks,
        nb_total_benchs=len(benchmarks),
        max_rows=15,
        last_updated=datetime.now(),
    )


def copy_static(benchmark=None):
    """ Copy static files in the HTML output folder """
    if benchmark is not None:
        dst = benchmark / HTML_DIR / 'static'
    else:
        dst = HTML_DIR / 'static'
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(ROOT / 'static', dst)


def render_all_results(results, benchmark, local=True):
    """ Create an html file containing the plot from a benchmark run. """
    if local:
        template = TEMPLATE_LOCAL_RESULT
    else:
        template = TEMPLATE_RESULT
    htmls = []
    for result in results:
        html = Template(
            filename=str(template),
            input_encoding="utf-8").render(
            result=result,
            benchmark=benchmark,
        )
        htmls.append(html)
    return htmls


def plot_benchmark_html(df, output_dir, kinds,
                        display=True, index=False):
    """
    Plot convergence curves and histograms for a
    given benchmark in an HTML file using plotly.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.
    benchmark_instance : Benchmark
        The benchmark instance.
    display : bool
        If set to True, display the curves by opening
        the default browser.

    Returns
    -------
    None
    """

    benchmark = output_dir
    print("Building html files")

    copy_static(benchmark)
    print(f'Rendering benchmark: {benchmark}')

    Path(benchmark / HTML_DIR).mkdir(exist_ok=True)
    Path(benchmark / HTML_DIR_FIGURES).mkdir(exist_ok=True, parents=True)
    Path(benchmark / HTML_DIR_OUTPUTS).mkdir(exist_ok=True, parents=True)

    results = get_result_from_df(df, kinds)
    htmls = render_all_results(results, benchmark)

    result_filename = benchmark / HTML_DIR / results[0]['page']
    print(f"Writing results to {result_filename}")
    with open(result_filename, "w") as f:
        f.write(htmls[0])

    if display:
        webbrowser.open(str(result_filename), new=2)


def plot_benchmark_html_all(patterns=(), benchmarks=(), root=None):
    """ Generate a HTML file for all benchmarks in outputs """
    if not benchmarks:
        benchmarks = [
            f.name for f in (root / 'outputs').iterdir() if f.is_dir()
        ]
    if not patterns:
        patterns = ['*']

    copy_static()

    rendered = render_index(benchmarks)
    index_filename = HTML_DIR / 'index.html'
    print(f"Writing index to {index_filename}")
    with open(index_filename, "w") as f:
        f.write(rendered)

    for benchmark in benchmarks:
        print(f'Rendering benchmark: {benchmark}')

        Path(HTML_DIR / benchmark).mkdir(exist_ok=True)
        Path(HTML_DIR_FIGURES / benchmark).mkdir(exist_ok=True, parents=True)
        Path(HTML_DIR_OUTPUTS / benchmark).mkdir(exist_ok=True, parents=True)

        fnames = []
        for p in patterns:
            fnames += glob.glob(f'outputs/{benchmark}/{p}.csv')
        fnames = sorted(set(fnames))
        results = get_results(fnames, PLOT_KINDS.keys(), copy=True)
        rendered = render_benchmark(results, benchmark)

        benchmark_filename = HTML_DIR / f"{benchmark}.html"
        print(f"Writing {benchmark} results to {benchmark_filename}")
        with open(benchmark_filename, "w") as f:
            f.write(rendered)

        htmls = render_all_results(results, benchmark, local=False)
        for result, html in zip(results, htmls):
            result_filename = HTML_DIR / result['page']
            print(f"Writing results to {result_filename}")
            with open(result_filename, "w") as f:
                f.write(html)
