import itertools
import pandas as pd
import matplotlib.pyplot as plt

# helpers to manage metadata in the parquet files
from ..utils.parquet import get_metadata
from ..utils.parquet import update_metadata

from ..constants import PLOT_KINDS
from .helpers import get_plot_id
from .plot_boxplot import plot_boxplot  # noqa: F401
from .plot_bar_chart import plot_bar_chart  # noqa: F401
from .generate_html import plot_benchmark_html
from .generate_matplotlib import get_figures


BACKWARD_COMPAT_PLOTS = {
    "objective_curve": "objective_curve",
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

    if "plots" not in config or config["plots"] is None:
        config["plots"] = (
            list(PLOT_KINDS.keys()) +
            benchmark.get_custom_plot_names()
        )

    if html:
        plot_benchmark_html(fname, benchmark, config, display)

    # TODO: rewrite this when default plots are also custom plots
    else:
        # Load the results.
        if fname.suffix == '.parquet':
            df = pd.read_parquet(fname)
        else:
            df = pd.read_csv(fname)
        if "data_name" in df.columns:
            df = df.rename(columns={"data_name": "dataset_name"})

        obj_cols = [
            k for k in df.columns
            if k.startswith('objective_') and k != 'objective_name'
        ]
        datasets = df['dataset_name'].unique()
        output_dir = benchmark.get_output_folder()

        valid_kinds = (
            list(PLOT_KINDS.keys()) + benchmark.get_custom_plot_names()
        )
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

        for data in datasets:
            df_data = df[df['dataset_name'] == data]
            objective_names = df['objective_name'].unique()
            for objective_name in objective_names:
                df_obj = df_data[df_data['objective_name'] == objective_name]

                plot_id = get_plot_id(benchmark.name, df_obj)

                for kind, obj_col in itertools.product(
                        config["plots"], obj_cols
                ):
                    if kind not in PLOT_KINDS:
                        continue
                    # For now only plot bar chart and suboptimality for
                    # objective_value for which we monitor convergence
                    # XXX - find a better solution
                    if obj_col != "objective_value" and (
                            kind == "bar_chart" or "subopt" in kind):
                        continue
                    plot_func = globals()[PLOT_KINDS[kind]]
                    try:
                        fig = plot_func(df_obj, obj_col=obj_col, plotly=plotly)
                    except TypeError:
                        fig = plot_func(df_obj, obj_col=obj_col)
                    save_name = output_dir / f"{plot_id}_{obj_col}_{kind}"
                    if hasattr(fig, 'write_html'):
                        save_name = save_name.with_suffix('.html')
                        fig.write_html(str(save_name), include_mathjax='cdn')
                    else:
                        save_name = save_name.with_suffix('.pdf')
                        plt.savefig(save_name)
                    print(f'Save {kind} plot of {obj_col} for {data} and '
                          f'{objective_name} as: {save_name}')
                    figs.append(fig)
        if display:
            plt.show()
        return figs
