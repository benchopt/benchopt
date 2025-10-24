import pandas as pd
import matplotlib.pyplot as plt

# helpers to manage metadata in the parquet files
from ..utils.parquet import get_metadata
from ..utils.parquet import update_metadata

from .generate_html import plot_benchmark_html
from .generate_matplotlib import get_figures


def plot_benchmark(fname, benchmark, kinds=None, display=True, plotly=False,
                   html=True):
    """Plot convergence curve and bar chart for a given benchmark.

    Parameters
    ----------
    fname : str
        Name of the file in which the results are saved.
    benchmark : benchopt.Benchmark object
        Object to represent the benchmark.
    kinds : list of str or None
        List of the plots that will be generated. If None are provided, use the
        config file to choose or default to suboptimality_curve.
    display : bool
        If set to True, display the curves with plt.show.
    plotly : bool
        If set to True, generate figures with plotly if possible and save the
        result as a HTML file.
    html : bool
        If True plot the benchmark in an HTML page. If True, plotly
        is necessarily used.

    Returns
    -------
    figs : list
        The matplotlib figures for convergence curve and bar chart
        for each dataset.
    """
    config = get_metadata(fname)
    params = ["plots", "plot_configs"]
    for param in params:
        options = benchmark.get_setting(param, default_config=config)
        if options is not None:
            config[param] = options

    update_metadata(fname, config)

    if kinds is not None and len(kinds) > 0:
        config["plots"] = kinds

    if "plots" not in config or config["plots"] is None:
        config["plots"] = benchmark.get_custom_plot_names()

    if html:
        plot_benchmark_html(fname, benchmark, config, display)

    # TODO: rewrite this when default plots are also custom plots
    else:
        # Load the results.
        if fname.suffix == '.parquet':
            df = pd.read_parquet(fname)
        else:
            df = pd.read_csv(fname)

        output_dir = benchmark.get_output_folder()

        valid_kinds = benchmark.get_custom_plot_names()

        for kind in config["plots"]:
            if kind not in valid_kinds:
                raise ValueError(
                    f"Invalid plot kind '{kind}'. Available kinds are: "
                    f"{valid_kinds}"
                )

        figs = []

        kind_figs = get_figures(
            benchmark, df, output_dir, config["plots"]
        )
        figs.extend(kind_figs)

        if display:
            plt.show()
        return figs
