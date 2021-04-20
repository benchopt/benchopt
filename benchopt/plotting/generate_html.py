import json
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
DEFAULT_HTML_DIR = Path("html")
OUTPUTS = "outputs"
FIGURES = "figures"

TEMPLATE_INDEX = ROOT / "templates" / "index.mako.html"
TEMPLATE_BENCHMARK = ROOT / "templates" / "benchmark.mako.html"
TEMPLATE_RESULT = ROOT / "templates" / "result.mako.html"
TEMPLATE_LOCAL_RESULT = ROOT / "templates" / "local_result.mako.html"


def generate_plot_benchmark(df, kinds, fname, fig_dir, benchmark_name):
    """Generate all possible plots for a given benchmark run.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.
    kinds : list of str
        List of the kind of plots that will be generated. This needs to be a
        sub-list of PLOT_KINDS.keys().
    fname: str
        CSV file name.
    fig_dir : Path
        Base directory to save figures.
    benchmark_name : str
        Name of the benchmark, to prefix the file names.

    Returns
    -------
    dict
        The figures for convergence curves and histograms
        for each dataset.
    """
    dataset_names = df['data_name'].unique()
    objective_names = df['objective_name'].unique()

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
                    fig, f"{benchmark_name}_{fname.name}_{n_figure}", fig_dir
                )
                n_figure += 1

    return dict(
        figures=figures, dataset_names=dataset_names, fname_short=fname.name,
        objective_names=objective_names, kinds=list(kinds)
    )


def export_figure(fig, fig_name, fig_dir):
    """Export a figure to HTML or svg.

    Parameters
    ----------
    fig : plotly.graph_objs.Figure
        Figure from plotly
    fig_name : str
        Name to be given to the figure.
    fig_dir : Path
        Base directory to save figures.

    Returns
    -------
    save_name : str
        Path to the saved figure.
    """
    if hasattr(fig, 'to_html'):
        return fig.to_html(include_plotlyjs=False)

    fig_basename = f"{fig_name}.svg"
    save_name = fig_dir / fig_basename
    fig.savefig(save_name)
    plt.close(fig)
    return str(save_name)


def get_results(fnames, kinds, root_html, benchmark_name, copy=False):
    """Generate figures from a list of csv files.

    Parameters
    ----------
    fnames : list of Path
        list of csv files containing the benchmark results.
    kinds : list of str
        List of the kind of plots that will be generated. This needs to be a
        sub-list of PLOT_KINDS.keys().
    root_html : Path
        Directory where all the HTML files related to the benchmark are stored.
    benchmark_name : str
        Name of the benchmark, to prefix all files.
    copy : bool (default: False)
        If set to True, copy each file in the root_html / OUTPUTS
        directory, to make sure it can be downloaded.

    Returns
    -------
    results : dict
        Dictionary containing all the info on each run and the links to the
        generated figures.
    """
    results = []
    fig_dir = root_html / FIGURES
    out_dir = root_html / OUTPUTS

    for fname in fnames:
        print(f"Processing {fname}")

        df = pd.read_csv(fname)
        datasets = list(df['data_name'].unique())

        # Copy CSV if necessary and give a relative path for HTML page access
        if copy:
            fname_in_output = out_dir / f"{benchmark_name}_{fname.name}"
            shutil.copy(fname, fname_in_output)
            fname = fname_in_output
        fname = fname.relative_to(root_html)

        # Generate figures
        result = dict(
            fname=fname, datasets=datasets,
            **generate_plot_benchmark(
                df, kinds, fname, fig_dir, benchmark_name
            )
        )
        results.append(result)

    for result in results:
        result['page'] = (
            f"{benchmark_name}_"
            f"{result['fname_short'].replace('.csv', '.html')}"
        )

    return results


def render_index(benchmark_names, static_dir):
    """Render a result index home page for all rendered benchmarks.

    Parameters
    ----------
    benchmark_names : list of str
        A list of all benchmark names that have been rendered.

    Returns
    -------
    rendered : str
        A str with the HTML code for the index page.
    """
    return Template(
        filename=str(TEMPLATE_INDEX), input_encoding="utf-8"
    ).render(
        benchmarks=benchmark_names,
        nb_total_benchs=len(benchmark_names),
        max_rows=15, static_dir=static_dir,
        last_updated=datetime.now(),
    )


def render_benchmark(results, benchmark_name, static_dir, home='index.html'):
    """Render a page indexing all runs for one benchmark.

    Parameters
    ----------
    results : list of Path
        List of all the run available for this benchmark.
    benchmark_name : str
        Named of the rendered benchmark.
    static_dir : str
        Relative path from HTML root to the static files.
    home : str
        URL of the home page.

    Returns
    -------
    rendered : str
        A str with the HTML code for the benchmark page.
    """
    return Template(
        filename=str(TEMPLATE_BENCHMARK), input_encoding="utf-8"
    ).render(
        results=results,
        benchmark=benchmark_name,
        max_rows=15, nb_total_benchs=len(results),
        last_updated=datetime.now(),
        static_dir=static_dir, home=home
    )


def render_all_results(results, benchmark_name, static_dir, home='index.html'):
    """Create an html file containing the plots from a benchmark run.

    Parameters
    ----------
    results : list of dict
        List of all the run that have been rendered for this benchmark.
    benchmark_name : str
        Named of the rendered benchmark.
    static_dir : str
        Relative path from HTML root to the static files.
    home : str
        URL of the home page.

    Returns
    -------
    htmls : list of str
        A List of str contraining the HTML code for each benchmark run.
    """
    template = TEMPLATE_RESULT
    htmls = []
    for result in results:
        html = Template(
            filename=str(template),
            input_encoding="utf-8"
        ).render(
            result=result,
            benchmark=benchmark_name,
            static_dir=static_dir,
            home=home
        )
        htmls.append(html)
    return htmls


def copy_static(root_html=None):
    "Copy static files in the HTML output folder."
    if root_html is None:
        root_html = DEFAULT_HTML_DIR
    static_dir = root_html / 'static'
    if static_dir.exists():
        shutil.rmtree(static_dir)
    shutil.copytree(ROOT / 'static', static_dir)
    return static_dir.relative_to(root_html)


def _fetch_cached_run_list(new_results, benchmark_html):

    # Load/update and dump a cache of the previous new_results to maintain
    # an up to date list of runs.
    benchmark_html_cache = benchmark_html / 'cache_run_list.json'
    new_results = {
        str(r['fname']): {
            'fname': str(r['fname']), 'fname_short': str(r['fname_short']),
            'page': str(r['page']), 'datasets': r['datasets']
        } for r in new_results
    }
    if benchmark_html_cache.exists():
        results = json.loads(benchmark_html_cache.read_text())
    else:
        results = {}
    results.update(new_results)
    benchmark_html_cache.write_text(json.dumps(results))

    return list(results.values())


def plot_benchmark_html(fnames, benchmark, kinds,
                        display=True, index=False):
    """Plot a given benchmark as an HTML report. This function can either plot
    a single run or multiple ones.

    Parameters
    ----------
    fnames : list of Path or Path
        Name of the file in which the results are saved.
    benchmark : benchopt.Benchmark object
        Object to represent the benchmark.
    kinds : list of str
        List of the kind of plots that will be generated. This needs to be a
        sub-list of PLOT_KINDS.keys().
    display : bool
        If set to True, display the curves by opening
        the default browser.

    Returns
    -------
    None
    """
    if isinstance(fnames, Path):
        fnames = [fnames]

    # Get HTML folder for the benchmark and make sure it contains
    # figures directory and static files.
    root_html = benchmark.get_output_folder()
    (root_html / FIGURES).mkdir(exist_ok=True)
    static_dir = copy_static(root_html)
    bench_index = (root_html / benchmark.name).with_suffix('.html')
    home = bench_index.relative_to(root_html)

    # Create the figures and render the page as a html.
    results = get_results(fnames, kinds, root_html, benchmark.name)
    htmls = render_all_results(
        results, benchmark.name, static_dir=static_dir, home=home
    )

    # Save the resulting page in the HTML folder
    for result, html in zip(results, htmls):
        result_filename = root_html / result['page']
        print(f"Writing results to {result_filename}")
        with open(result_filename, "w") as f:
            f.write(html)

    # Fetch run list from the benchmark and update the benchmark front page.
    run_list = _fetch_cached_run_list(results, root_html)
    rendered = render_benchmark(
        run_list, benchmark.name, static_dir=static_dir, home=home
    )
    print(f"Writing {benchmark.name} results to {bench_index}")
    with open(bench_index, "w") as f:
        f.write(rendered)

    # Display the file in the default browser
    if display:
        result_filename = (root_html / results[-1]['page']).absolute()
        webbrowser.open_new_tab('file://' + str(result_filename))


def plot_benchmark_html_all(patterns=(), benchmarks=(), root=None,
                            display=True):
    """Generate a HTML rerport for multiple benchmarks.

    This utility is the one used to create https://benchopt.github.io/results.
    It will open all benchmarks in `root` and create a website to browse them.

    Parameters
    ----------
    patterns : tuple of str
        Only include result files that match the provided patterns.
    benchmarks : tuple of Path
        Explicitly provides the benchmarks that should be display in the
        report.
    root : Path | None
        If no benchmarks is provided, list all directory in root that have
        a `outputs` folder and generate the report.
    display : bool
        If set to True, open the HTML report in default browser.

    Returns
    -------
    None
    """
    # Parse the arguments adn get the list of benchmarks and patterns.
    if not benchmarks:
        root = Path(root)
        benchmarks = [
            f for f in root.iterdir()
            if f.is_dir() and (f / 'outputs').is_dir()
        ]
    else:
        benchmarks = [Path(b) for b in benchmarks]
    if not patterns:
        patterns = ['*']

    # make sure the `html` folder exists and copy static files.
    root_html = DEFAULT_HTML_DIR
    (root_html / FIGURES).mkdir(exist_ok=True, parents=True)
    (root_html / OUTPUTS).mkdir(exist_ok=True, parents=True)
    static_dir = copy_static()

    # Create an index that referes all benchmarks.
    rendered = render_index([b.name for b in benchmarks], static_dir)
    index_filename = DEFAULT_HTML_DIR / 'index.html'
    print(f"Writing index to {index_filename}")
    with open(index_filename, "w") as f:
        f.write(rendered)

    # Loop over all benchmarks to
    for benchmark in benchmarks:
        print(f'Rendering benchmark: {benchmark}')

        fnames = []
        for p in patterns:
            fnames += (benchmark / 'outputs').glob(f"{p}.csv")
        fnames = sorted(set(fnames))
        results = get_results(
            fnames, PLOT_KINDS.keys(), root_html, benchmark.name, copy=True
        )

        rendered = render_benchmark(
            results, benchmark.name, static_dir=static_dir
        )

        benchmark_filename = (root_html / benchmark.name).with_suffix('.html')
        print(f"Writing {benchmark.name} results to {benchmark_filename}")
        with open(benchmark_filename, "w") as f:
            f.write(rendered)

        htmls = render_all_results(
            results, benchmark.name, static_dir=static_dir
        )
        for result, html in zip(results, htmls):
            result_filename = root_html / result['page']
            print(f"Writing results to {result_filename}")
            with open(result_filename, "w") as f:
                f.write(html)

    # Display the file in the default browser
    if display:
        webbrowser.open_new_tab('file://' + str(index_filename.absolute()))
