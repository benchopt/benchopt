import pandas as pd
import matplotlib.pyplot as plt

# helpers to manage metadata in the parquet files
from ..utils.parquet import get_metadata
from ..utils.parquet import update_metadata

from .generate_html import plot_benchmark_html
from .generate_matplotlib import get_figures


BACKWARD_COMPAT_PLOTS = {
    "suboptimality_curve": "objective_curve",
    "relative_suboptimality_curve": "objective_curve"
}


def sanitize_config(config):
    """Flatten a pytree into a list."""
    if isinstance(config, (list, tuple)):
        # Avoid duplicates while preserving order
        seen = set()
        return [
            sanitize_config(item) for item in config
            if item not in seen and not seen.add(item)
        ]
    elif isinstance(config, dict):
        return {
            k: sanitize_config(v) for k, v in config.items()
        }
    else:
        return BACKWARD_COMPAT_PLOTS.get(config, config)


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
    plot_config = get_metadata(fname)
    plot_config = benchmark.get_plot_config(default_config=plot_config)
    plot_config = sanitize_config(plot_config)
    update_metadata(fname, plot_config)

    if kinds is not None and len(kinds) > 0:
        plot_config["plots"] = kinds

    valid_kinds = benchmark.get_plot_names()

    if "plots" not in plot_config or plot_config["plots"] is None:
        plot_config["plots"] = valid_kinds

    if html:
        plot_benchmark_html(fname, benchmark, plot_config, display)

    else:
        # Load the results.
        if fname.suffix == '.parquet':
            df = pd.read_parquet(fname)
        else:
            df = pd.read_csv(fname)
        if "data_name" in df.columns:
            df = df.rename(columns={"data_name": "dataset_name"})

        output_dir = benchmark.get_output_folder()

        for kind in plot_config["plots"]:
            if kind not in valid_kinds:
                raise ValueError(
                    f"Invalid plot kind '{kind}'. Available kinds are: "
                    f"{valid_kinds}"
                )

        figs = []

        kind_figs = get_figures(
            benchmark, df, output_dir, plot_config["plots"]
        )
        figs.extend(kind_figs)

        if display:
            plt.show()
        return figs
