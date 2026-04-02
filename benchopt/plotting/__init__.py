import warnings
import matplotlib.pyplot as plt

# helpers to manage metadata in the parquet files
from ..results import read_results
from ..results.parquet import get_metadata
from ..results.parquet import update_metadata

from .generate_html import plot_benchmark_html
from .generate_matplotlib import get_figures


BACKWARD_COMPAT_PLOTS = {
    "suboptimality_curve": "objective_curve",
    "relative_suboptimality_curve": "objective_curve"
}

ALL_PLOT_OPTIONS = [
    "scale", "with_quantiles", "suboptimal_curve", "relative_curve",
    "hidden_curves", "plot_kind"
]


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


def check_view(name, view, plots):
    all_options = ALL_PLOT_OPTIONS
    all_kinds = [plot._get_name() for plot in plots]

    kind = view.get("plot_kind")
    if kind is None:
        warnings.warn(f"View {name} has no 'plot_kind' specified.")
    elif kind not in all_kinds:
        warnings.warn(
            f"View '{name}' has invalid plot_kind '{kind}'. "
            "Valid kinds are:\n-" + "\n-".join(all_kinds)
        )
        return
    else:
        plot = next(plot for plot in plots if plot._get_name() == kind)
        all_options += [
            f"{kind}_{p}" if p != "plot_kind" else p
            for p in plot.options.keys()
        ]

    all_options = set(all_options)
    mismatched_options = set(view.keys()) - all_options
    if mismatched_options:
        warnings.warn(
            f"View '{name}' has options {mismatched_options} which are "
            f"not known for plot_kind {kind}. Valid options are:\n-"
            + "\n-".join(all_options)
        )


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

    plots = benchmark.get_plots()
    valid_kinds = [plot._get_name() for plot in plots]

    if "plots" not in plot_config or plot_config["plots"] is None:
        plot_config["plots"] = valid_kinds

    for kind in plot_config["plots"]:
        if kind not in valid_kinds:
            raise ValueError(
                f"Invalid plot kind '{kind}' specified in plot config. "
                "This config is either set in the config.yml file in the "
                "benchmark directory or in the {benchmark.name} section of "
                "global benchopt config."
                "Available kinds are:\n-" + "\n-".join(valid_kinds)
            )

    for name, view in plot_config.get("plot_configs", {}).items():
        check_view(name, view, plots)

    if html:
        plot_benchmark_html(fname, benchmark, plot_config, display)

    else:
        # Load the results.
        df = read_results(fname)

        output_dir = benchmark.get_output_folder()

        figs = []

        kind_figs = get_figures(
            benchmark, df, output_dir, plot_config["plots"]
        )
        figs.extend(kind_figs)

        if display:
            plt.show()
        return figs
