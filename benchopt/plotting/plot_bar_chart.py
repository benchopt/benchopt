import numpy as np

from .helpers import _color_palette
from .helpers_compat import get_figure, _make_bars

PLOTLY_GRAY = (.8627, .8627, .8627)


def plot_bar_chart(df, obj_col='objective_value', plotly=False):
    """Plot bar chart for a given benchmark and dataset.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.
    obj_col : str
        Column to select in the DataFrame for the plot.
    plotly : bool
        If set to True, creates a figure with plotly instead of matplotlib.

    Returns
    -------
    fig : instance of matplotlib.figure.Figure
        The matplotlib figure of the objective values.
    """
    solver_names = df['solver_name'].unique()
    dataset_name = df['data_name'].unique()[0]
    objective_name = df['objective_name'].unique()[0]
    n_solvers = len(solver_names)

    eps = 1e-6
    width = 1 / (n_solvers + 2)
    colors = _color_palette(n_solvers)

    height_list = []
    ticks_list = []
    times_list = []
    fig = get_figure(plotly)
    c_star = df[obj_col].min() + eps
    for i, solver_name in enumerate(solver_names):
        xi = (i + 1.5) * width
        ticks_list.append((xi, solver_name))
        df_ = df[df['solver_name'] == solver_name]

        # Find the first stop_val which reach a given tolerance
        df_tol = df_.groupby('stop_val').filter(
            lambda x: x[obj_col].max() < c_star)
        if df_tol.empty:
            colors[i] = "w" if not plotly else PLOTLY_GRAY
            print(f"Solver {solver_name} did not reach precision {eps}.")
            height_list.append(df.time.max())
            times_list.append(np.nan)
            continue
        stop_val = df_tol['stop_val'].min()
        this_df = df_[df_['stop_val'] == stop_val]
        height_list.append(this_df['time'].median())
        times_list.append(this_df['time'])

    _make_bars(fig, height_list, ticks_list, width,
               colors, times_list, plotly=plotly)
    title = f"{objective_name}\nData: {dataset_name}"

    if plotly:
        fig.update_layout(
            yaxis_type='log',
            yaxis_title="Time [sec]",
            yaxis_tickformat=".1e",
            xaxis_tickangle=-60,
            xaxis_tickmode='array',
            xaxis_ticktext=solver_names,
            xaxis_tickvals=[xi for xi, _ in ticks_list],
            xaxis_range=[0, 1],
            title=title
        )
    else:
        ax = fig.gca()
        ax.set_xticks([xi for xi, _ in ticks_list])
        ax.set_xticklabels([label for _, label in ticks_list], rotation=60)
        ax.set_yscale('log')
        ax.set_xlim(0, 1)
        ax.set_ylabel("Time [sec]")
        ax.set_title(title, fontsize=12)
        fig.tight_layout()

    return height_list


def computeBarChartData(df, obj_col, solver):
    """Gives the list of bar chart values.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.
    obj_col : str
        Column to select in the DataFrame for the plot.
    plotly : bool
        If set to True, creates a figure with plotly instead of matplotlib.

    Returns
    -------
    list : bar chart values.
    """
    eps = 1e-6
    c_star = df[obj_col].min() + eps

    df_ = df[df['solver_name'] == solver]

    # Find the first stop_val which reach a given tolerance
    df_tol = df_.groupby('stop_val').filter(
        lambda x: x[obj_col].max() < c_star)
    if df_tol.empty:
        text = 'Did not converge'
        height = df.time.max()
        times = np.nan
    else:
        stop_val = df_tol['stop_val'].min()
        this_df = df_[df_['stop_val'] == stop_val]
        text = ''
        height = this_df['time'].median()
        times = this_df['time'].tolist()

    return dict(y=height, times=times, text=text)
