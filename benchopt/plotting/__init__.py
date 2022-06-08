import itertools
import pandas as pd
import matplotlib.pyplot as plt

from ..constants import PLOT_KINDS
from .helpers import get_plot_id
from .plot_bar_chart import plot_bar_chart  # noqa: F401
from .plot_objective_curve import plot_objective_curve  # noqa: F401
from .plot_objective_curve import plot_suboptimality_curve  # noqa: F401
from .plot_objective_curve import plot_relative_suboptimality_curve  # noqa: F401 E501
from .generate_html import plot_benchmark_html


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
    config_kinds = benchmark.get_setting('plots')
    if kinds is None or len(kinds) == 0:
        kinds = config_kinds

    if html:
        plot_benchmark_html(fname, benchmark, kinds, display)
        return None

    else:
        # Load the results.
        df = pd.read_csv(fname)
        obj_cols = [
            k for k in df.columns
            if k.startswith('objective_') and k != 'objective_name'
        ]
        datasets = df['data_name'].unique()
        output_dir = benchmark.get_output_folder()
        figs = []
        for data in datasets:
            df_data = df[df['data_name'] == data]
            objective_names = df['objective_name'].unique()
            for objective_name in objective_names:
                df_obj = df_data[df_data['objective_name'] == objective_name]

                plot_id = get_plot_id(benchmark.name, df_obj)

                for kind, obj_col in itertools.product(kinds, obj_cols):
                    if kind not in PLOT_KINDS:
                        raise ValueError(
                            f"Requesting invalid plot '{kind}'."
                            f"Should be in:\n{PLOT_KINDS}"
                        )
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
