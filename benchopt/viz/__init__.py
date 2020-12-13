import matplotlib.pyplot as plt

from ..config import get_benchmark_setting
from ..utils.files import _get_output_folder

from .helpers import get_plot_id
from .plot_histogram import plot_histogram
from .plot_suboptimality_curve import plot_suboptimality_curve
from .plot_suboptimality_curve import plot_relative_suboptimality_curve
from .plot_objective_curve import plot_objective_curve


PLOT_KINDS = {
    'suboptimality_curve': plot_suboptimality_curve,
    'relative_suboptimality_curve': plot_relative_suboptimality_curve,
    'objective_curve': plot_objective_curve,
    'histogram': plot_histogram
}


def plot_benchmark(df, benchmark, kinds=None, display=True):
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

    Returns
    -------
    figs : list
        The matplotlib figures for convergence curve and histogram
        for each dataset.
    """
    config_kinds = get_benchmark_setting(benchmark, 'plots')
    if kinds is None or len(kinds) == 0:
        kinds = config_kinds

    output_dir = _get_output_folder(benchmark)

    datasets = df['data_name'].unique()
    figs = []
    for data in datasets:
        df_data = df[df['data_name'] == data]
        objective_names = df['objective_name'].unique()
        for objective_name in objective_names:
            df_obj = df_data[df_data['objective_name'] == objective_name]

            plot_id = get_plot_id(benchmark, df_obj)

            for k in kinds:
                if k not in PLOT_KINDS:
                    raise ValueError(
                        f"Requesting invalid plot '{k}'. Should be in:\n"
                        f"{PLOT_KINDS}")
                fig = PLOT_KINDS[k](df_obj, benchmark)
                save_name = output_dir / f"{plot_id}_{k}.pdf"
                plt.savefig(save_name)
                print(f'Save {k} plot for {data} and {objective_name} as:'
                      f' {save_name}')
                figs.append(fig)
    if display:
        plt.show()
    return figs
