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


def sanitize_options(options):
    """Flatten a pytree into a list."""
    if isinstance(options, (list, tuple)):
        # Avoid duplicates while preserving order
        seen = set()
        return [
            sanitize_options(item) for item in options
            if item not in seen and not seen.add(item)
        ]
    elif isinstance(options, dict):
        return {
            k: sanitize_options(v) for k, v in options.items()
        }
    else:
        return BACKWARD_COMPAT_PLOTS.get(options, options)


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
            config[param] = sanitize_options(options)

    update_metadata(fname, config)

    if kinds is not None and len(kinds) > 0:
        config["plots"] = kinds

    valid_kinds = benchmark.get_plot_names()

    if "plots" not in config or config["plots"] is None:
        config["plots"] = valid_kinds

    if html:
        plot_benchmark_html(fname, benchmark, config, display)

    else:
        # Load the results.
        if fname.suffix == '.parquet':
            df = pd.read_parquet(fname)
        else:
            df = pd.read_csv(fname)
        if "data_name" in df.columns:
            df = df.rename(columns={"data_name": "dataset_name"})

        output_dir = benchmark.get_output_folder()

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
