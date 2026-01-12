import json
import shutil
import webbrowser
from pathlib import Path
from datetime import datetime
import pandas as pd
from mako.template import Template

from ..utils.parquet import get_metadata as get_parquet_metadata

from benchopt.benchmark import Benchmark
from .helpers import update_plot_data_style

ROOT = Path(__file__).parent / "html"
DEFAULT_HTML_DIR = Path("html")
OUTPUTS = "outputs"

TEMPLATE_INDEX = ROOT / "templates" / "index.mako.html"
TEMPLATE_BENCHMARK = ROOT / "templates" / "benchmark.mako.html"
TEMPLATE_RESULT = ROOT / "templates" / "result.mako.html"

SYS_INFO = {
    "main": [('system-cpus', 'cpu'),
             ('system-ram (GB)', 'ram (GB)'),
             ("version-cuda", 'cuda')
             ],
    "sub": [('platform', 'platform'),
            ('system-processor', 'processor'),
            ('env-OMP_NUM_THREADS', 'nb threads')
            ],
    "ter": [("version-numpy", "numpy"),
            ("version-scipy", "scipy")
            ]
}


# Populate static file dictionary
STATIC = {}
STATIC_DIR = ROOT / "static"

# List all assets in static dir.
for asset in STATIC_DIR.glob("**/*"):
    if not asset.is_file():
        continue
    STATIC[asset.relative_to(STATIC_DIR).name] = asset.read_text()


def get_results(fnames, html_root, benchmark, config=None, copy=False):
    """Generate figures from a list of result files.

    Parameters
    ----------
    fnames : list of Path
        list of result files containing the benchmark results.
    html_root : Path
        Directory where all the HTML files related to the benchmark are stored.
    benchmark : benchopt.Benchmark
        Object to represent the benchmark.
    config: dict (default: None)
        If given, allows to specify the plot options. If not given, it is
        retrieved from the metadata in the result files.
    copy : bool (default: False)
        If set to True, copy each file in the html_root / OUTPUTS
        directory, to make sure it can be downloaded.

    Returns
    -------
    results : dict
        Dictionary containing all the info on each run and the links to the
        generated figures.
    """
    results = []
    out_dir = html_root / OUTPUTS

    for fname in fnames:
        print(f"Processing {fname}")

        if fname.suffix == '.parquet':
            df = pd.read_parquet(fname)
        else:
            df = pd.read_csv(fname)
        if "data_name" in df.columns:
            df = df.rename(columns={"data_name": "dataset_name"})

        config_ = get_parquet_metadata(fname) if config is None else config
        # Sanitize the config for comparison with the plot names
        kinds = config_.get('plots', benchmark.get_plot_names())
        kinds = [f"{k.strip().lower().replace(' ', '_')}" for k in kinds]

        datasets = list(df['dataset_name'].unique())
        sysinfo = get_sysinfo(df)
        # Copy result file if necessary
        # and give a relative path for HTML page access
        if copy:
            fname_in_output = out_dir / f"{benchmark.name}_{fname.name}"
            shutil.copy(fname, fname_in_output)
            fname = fname_in_output
        fname = fname.absolute().relative_to(html_root.absolute())

        # Generate figures
        result = dict(
            fname=fname,
            fname_short=fname.name,
            datasets=datasets,
            sysinfo=sysinfo,
            dataset_names=df['dataset_name'].unique(),
            objective_names=df['objective_name'].unique(),
            obj_cols=[
                k for k in df.columns
                if k.startswith('objective_') and k != 'objective_name'
            ],
            kinds=kinds,
            metadata=get_metadata(df, config_.get('plot_configs', {})),
        )

        data, options = benchmark.get_plot_data(df, result['kinds'])
        data = update_plot_data_style(data, plotly=True)
        result['json_plots'] = json.dumps(data)
        result['plot_options'] = options

        results.append(result)

    for result in results:
        html_file_name = Path(result['fname_short']).with_suffix('.html').name
        result['page'] = f"{benchmark.name}_{html_file_name}"

    return results


def get_metadata(df, plot_configs):
    """Get the benchmark metadata.

    Metadata are already available among the columns of `df`.
    It might be Objective and/or Solvers description.

    Returns
    -------
    metadata: dict
        Dictionary containing the benchmark metadata.
    """
    metadata = {'plot_configs': plot_configs}

    # get solver descriptions
    # wrap in try-except block to preserve compatibility
    # with older versions
    try:
        solvers_description = df.groupby(
            by=["solver_name"]
        )["solver_description"].first()

        metadata["solvers_description"] = solvers_description.to_dict()
    except KeyError:
        metadata["solvers_description"] = {}

    # to avoid conflicts with objective metrics
    # get objective description and use `obj_` instead of `objective_`
    # try-except block to preserve compatibility with benchopt <= v1.3.1
    try:
        obj_description = df["obj_description"].unique()[0]
        metadata["obj_description"] = obj_description
    except KeyError:
        metadata["obj_description"] = ""

    return metadata


def get_sysinfo(df):
    """Get a dictionnary of the recorded system informations.

    System informations are sorted in 3 levels: main, sub and ter.
        - Main : cpu - ram - cuda.
            Displayed directly in the benchmark and result pages
            and can be filtered on.
        - Sub : platform - processor - number of threads.
            Displayed on click in the benchmark and results pages.
        - Ter : numpy - scipy.
            Displayed on click in the result page.

    Parameters
    ----------
    df : pandas.DataFrame
        recorded data from the Benchmark

    Returns
    -------
    sysinfo : dict
        Contains the three-level sytem informations.
    """

    def get_val(df, key):
        if key in df:
            if key == 'platform':
                return (
                    str(df["platform"].unique()[0]) +
                    str(df["platform-release"].unique()[0]) + "-" +
                    str(df["platform-architecture"].unique()[0])
                )
            else:
                df['version-numpy'] = df['version-numpy'].astype(str)
                val = df[key].unique()[0]
                if not pd.isnull(val):
                    return str(val)
                return ''
        else:
            return ''
    sysinfo = {
        level: {name: get_val(df, key) for key, name in keys}
        for level, keys in SYS_INFO.items()
    }
    return sysinfo


def render_index(benchmarks):
    """Render a result index home page for all rendered benchmarks.

    Parameters
    ----------
    benchmark : list of benchopt.Benchmark
        A list of all benchmarks that have been rendered.

    Returns
    -------
    rendered : str
        A str with the HTML code for the index page.
    """

    benchmarks.sort(key=lambda x: x.pretty_name)

    return Template(
        filename=str(TEMPLATE_INDEX), input_encoding="utf-8"
    ).render(
        benchmarks=benchmarks,
        nb_total_benchs=len(benchmarks),
        max_rows=15, static=STATIC,
        last_updated=datetime.now(),
    )


def render_benchmark(results, benchmark, home='index.html'):
    """Render a page indexing all runs for one benchmark.

    Parameters
    ----------
    results : list of Path
        List of all the run available for this benchmark.
    benchmark : benchopt.Benchmark
        Object to represent the benchmark.
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
        benchmark=benchmark,
        max_rows=15,
        last_updated=datetime.now(),
        static=STATIC, home=home
    )


def render_all_results(results, benchmark, home='index.html'):
    """Create an html file containing the plots from a benchmark run.

    Parameters
    ----------
    results : list of dict
        List of all the run that have been rendered for this benchmark.
    benchmark : benchopt.Benchmark
        Object to represent the benchmark.
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
            input_encoding="utf-8",
            strict_undefined=True
        ).render(
            result=result,
            benchmark=benchmark.name,
            static=STATIC, home=home
        )
        htmls.append(html)
    return htmls


def _fetch_cached_run_list(new_results, benchmark_html):
    # Load/update and dump a cache of the previous new_results to maintain
    # an up to date list of runs.
    benchmark_html_cache = benchmark_html / 'cache_run_list.json'
    new_results = {
        str(r['fname']): {
            'fname': str(r['fname']), 'fname_short': str(r['fname_short']),
            'sysinfo': r['sysinfo'],
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


def plot_benchmark_html(
        fnames, benchmark, config=None, display=True, html_home=None
):
    """Plot a given benchmark as an HTML report. This function can either plot
    a single run or multiple ones.

    Parameters
    ----------
    fnames : list of Path or Path
        Name of the file in which the results are saved.
    benchmark : benchopt.Benchmark
        Object to represent the benchmark.
    config: dict (default: None)
        Configuration for the different kind of plots.
    display : bool
        If set to True, display the curves by opening
        the default browser.
    html_home : str
        Index of the HTML website. This default to the benchmark index. This
        argument can be used to pass the index file when generating the full
        result website.
    """
    if isinstance(fnames, Path):
        fnames = [fnames]

    # Get HTML root folder for the benchmark and setup the different path.
    if html_home is None:
        html_root = benchmark.get_output_folder()
        bench_index = (html_root / benchmark.name).with_suffix('.html')
        html_home = bench_index
        copy = False
    else:
        html_root = html_home.parent
        bench_index = (html_root / benchmark.name).with_suffix('.html')
        copy = True

    # Make the link relative
    html_home = html_home.relative_to(html_root)

    # Create the figures and render the page as a html.
    results = get_results(fnames, html_root, benchmark, config, copy=copy)
    htmls = render_all_results(results, benchmark, home=html_home)

    # Save the resulting page in the HTML folder
    for result, html in zip(results, htmls):
        result_filename = html_root / result['page']
        result_filename.parent.mkdir(exist_ok=True)
        print(f"Writing results to {result_filename}")
        with open(result_filename, "w", encoding="utf-8") as f:
            f.write(html)

    if copy:
        run_list = results
    else:
        run_list = _fetch_cached_run_list(results, html_root)

    # Fetch run list from the benchmark and update the benchmark front page.
    rendered = render_benchmark(run_list, benchmark, home=html_home)
    print(f"Writing {benchmark.name} results to {bench_index}")
    with open(bench_index, "w", encoding="utf-8") as f:
        f.write(rendered)

    print("Rendering benchmark results...")
    # Display the file in the default browser
    if display:
        result_filename = (html_root / results[-1]['page']).absolute()
        webbrowser.open_new_tab('file://' + str(result_filename))


def plot_benchmark_html_all(patterns=(), benchmark_paths=(), root=None,
                            display=True):
    """Generate a HTML report for multiple benchmarks.

    This utility is the one used to create https://benchopt.github.io/results.
    It will open all benchmarks in `root` and create a website to browse them.

    Parameters
    ----------
    patterns : tuple of str
        Only include result files that match the provided patterns.
    benchmark_paths : tuple of Path
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
    if not benchmark_paths:
        root = Path(root)
        benchmarks = [
            Benchmark(f, allow_meta_from_json=True) for f in root.iterdir()
            if f.is_dir() and (f / 'outputs').is_dir() and f.name != "html"
        ]
        benchmark_paths = [b.benchmark_dir for b in benchmarks]
    else:
        benchmark_paths = [
            Benchmark(
                Path(b).resolve(), allow_meta_from_json=True
                ).benchmark_dir
            for b in benchmark_paths
            if Path(b).name != 'html'
        ]
    if not patterns:
        patterns = ['*']

    if len(benchmark_paths) == 0:
        raise ValueError(
            "Could not find any benchmark to render. Check that the provided "
            "root folder contains at least one benchmark."
        )

    benchmarks = [
        Benchmark(p, allow_meta_from_json=True)
        for p in benchmark_paths
    ]

    # make sure the `html` folder exists
    html_root = DEFAULT_HTML_DIR
    index_filename = html_root / 'index.html'
    (html_root / OUTPUTS).mkdir(exist_ok=True, parents=True)

    # Loop over all benchmark paths to create the associated result pages
    for benchmark_path, benchmark in zip(benchmark_paths, benchmarks):
        print(f'Rendering benchmark: {benchmark}')
        result_files = list(filter(
            lambda path: any(path.match(p) for p in patterns),
            benchmark.get_result_file('all')
        ))
        # Store the number of rendered results so we can easily generate the
        # index page with the number of available result files.
        benchmark.n_runs = len(result_files)
        if len(result_files) > 0:
            plot_benchmark_html(
                result_files, benchmark, config=None, display=False,
                html_home=index_filename
            )

    # Create an index that lists all benchmarks.
    rendered = render_index(benchmarks)
    print(f"Writing index to {index_filename}")
    with open(index_filename, "w", encoding="utf-8") as f:
        f.write(rendered)

    # Display the file in the default browser
    if display:
        webbrowser.open_new_tab('file://' + str(index_filename.absolute()))
