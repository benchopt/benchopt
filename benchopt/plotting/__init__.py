import matplotlib.pyplot as plt

from .helpers import get_plot_id
from .plot_histogram import plot_histogram
from .plot_objective_curve import plot_objective_curve
from .plot_objective_curve import plot_suboptimality_curve
from .plot_objective_curve import plot_relative_suboptimality_curve


PLOT_KINDS = {
    'suboptimality_curve': plot_suboptimality_curve,
    'relative_suboptimality_curve': plot_relative_suboptimality_curve,
    'objective_curve': plot_objective_curve,
    'histogram': plot_histogram
}


def plot_benchmark(df, benchmark, kinds=None, display=True, plotly=False):
    """Plot convergence curve and histogram for a given benchmark.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.
    benchmark : str
        The path to the benchmark folder.
    kinds : list of str or None
        List of the plots that will be generated. If None are provided, use the
        config file to choose or default to suboptimality_curve.
    display : bool
        If set to True, display the curves with plt.show.
    plotly : bool
        If set to True, generate figures with plotly if possible and save the
        result as a HTML file.

    Returns
    -------
    figs : list
        The matplotlib figures for convergence curve and histogram
        for each dataset.
    """
    config_kinds = benchmark.get_setting('plots')
    if kinds is None or len(kinds) == 0:
        kinds = config_kinds

    output_dir = benchmark.get_output_folder()

    datasets = df['data_name'].unique()
    figs = []
    for data in datasets:
        df_data = df[df['data_name'] == data]
        objective_names = df['objective_name'].unique()
        for objective_name in objective_names:
            df_obj = df_data[df_data['objective_name'] == objective_name]

            plot_id = get_plot_id(benchmark.name, df_obj)

            for k in kinds:
                if k not in PLOT_KINDS:
                    raise ValueError(
                        f"Requesting invalid plot '{k}'. Should be in:\n"
                        f"{PLOT_KINDS}")
                try:
                    fig = PLOT_KINDS[k](df_obj, plotly=plotly)
                except TypeError:
                    fig = PLOT_KINDS[k](df_obj)
                save_name = output_dir / f"{plot_id}_{k}"
                if hasattr(fig, 'write_html'):
                    save_name = save_name.with_suffix('.html')
                    fig.write_html(str(save_name), include_mathjax='cdn')
                else:
                    save_name = save_name.with_suffix('.pdf')
                    plt.savefig(save_name)
                print(f'Save {k} plot for {data} and {objective_name} as:'
                      f' {save_name}')
                figs.append(fig)
    if display:
        plt.show()
    return figs
