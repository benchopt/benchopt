import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

from .helpers_compat import get_figure
from .helpers_compat import add_h_line
from .helpers_compat import fill_between_y

CMAP = plt.get_cmap('tab10')
EPS = 1e-10


def _remove_prefix(text, prefix):
    return text[len(prefix):] if text.startswith(prefix) else text


def _get_curve_interp(df, obj_col, q_min, q_max):
    """Compute interpolation curve for a given solver.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results filtered for one solver.
    obj_col : str
        Column to select in the DataFrame for the plot.
    q_min, q_max : float
        The quantile to display the error bars in the plot.
    """
    n_interp = min(100, df.groupby('idx_rep').size().max())
    t = np.logspace(
        np.log10(df['time'].min()), np.log10(df['time'].max()), n_interp
    )
    curve_t = (
        df.groupby('idx_rep').apply(
            lambda x: pd.DataFrame({
                't': t,
                # Linear interpolator to resample on a grid t
                'v': interp1d(
                    x['time'], x[obj_col],
                    bounds_error=False,
                    fill_value=(
                        x[obj_col].iloc[0],
                        x[obj_col].iloc[-1]
                    )
                )(t)
            })
        )
    )
    curve_t = curve_t.groupby('t')['v'].quantile([0.5, q_min, q_max]).unstack()
    return curve_t


def plot_objective_curve(df, obj_col='objective_value', plotly=False,
                         suboptimality=False, relative=False, iteration=False):
    """Plot objective curve for a given benchmark and dataset.

    Plot the objective value F(x) as a function of the time.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.
    obj_col : str
        Column to select in the DataFrame for the plot.
    plotly : bool
        If set to True, output a plotly figure for HTML display.
    suboptimality : bool
        If set to True, remove the optimal objective value F(x^*). Here the
        value of F(x^*) is taken as the smallest value reached across all
        solvers.
    relative : bool
        If set to True, scale the objective value by 1 / F_0 where F_0 is
        computed as the largest objective value accross all initialization.
    iteration : bool
        If set to True, show the objective value as a function of the stop_val
        and not the time. Note that the stop val might not correspond between
        different solvers.

    Returns
    -------
    fig : matplotlib.Figure or pyplot.Figure
        The rendered figure, used to create HTML reports.
    """
    if plotly:
        markers = {i: i for i, v in enumerate(plt.Line2D.markers)}
    else:
        markers = {i: v for i, v in enumerate(plt.Line2D.markers)}

    df = df.copy()
    solver_names = df['solver_name'].unique()
    dataset_name = df['data_name'].unique()[0]
    objective_name = df['objective_name'].unique()[0]
    title = f"{objective_name}\nData: {dataset_name}"
    df.query(f"`{obj_col}` not in [inf, -inf]", inplace=True)
    y_label = "F(x)"
    if suboptimality:
        y_label = "F(x) - F(x*)"
        c_star = df[obj_col].min() - EPS
        df.loc[:, obj_col] -= c_star

    if relative:
        if suboptimality:
            y_label = "F(x) - F(x*) / F(x0) - F(x*)"
        else:
            y_label = "F(x) / F(x0)"
        max_f_0 = df[df['stop_val'] == 1][obj_col].max()
        df.loc[:, obj_col] /= max_f_0

    fig = get_figure(plotly)

    if df[obj_col].count() == 0:  # missing values
        if plotly:
            fig.add_annotation(text="Not Available",
                               xref="paper", yref="paper",
                               x=0.5, y=0.5, showarrow=False,
                               font=dict(color="black", size=32))
        else:
            plt.text(0.5, 0.5, "Not Available")
        return fig

    # use 2nd and 8th decile for now
    q_min, q_max = 0.2, 0.8
    for i, solver_name in enumerate(solver_names):
        df_ = df[df['solver_name'] == solver_name]

        if iteration:
            curve_t = (
                df_.groupby('stop_val')[obj_col]
                .quantile([q_min, 0.5, q_max]).unstack()
            )
        else:
            curve_t = _get_curve_interp(df_, obj_col, q_min=q_min, q_max=q_max)

        fill_between_y(
            fig, x=curve_t.index, y=curve_t[.5],
            q_min=curve_t[q_min], q_max=curve_t[q_max],
            color=CMAP(i % CMAP.N), marker=markers[i % len(markers)],
            label=solver_name, plotly=plotly
        )

    if iteration:
        x_label = 'Iteration'
        x_lim = (df['stop_val'].min(), df['stop_val'].max())
    else:
        x_label = "Time [sec]"
        x_lim = (df['time'].min(), df['time'].max())

    if suboptimality and not relative:
        add_h_line(fig, EPS, x_lim, plotly=plotly)

    # Format the plot to be nice
    if plotly:
        fig.update_layout(
            xaxis_type='linear',
            yaxis_type='log',
            xaxis_title=x_label,
            yaxis_title=y_label,
            yaxis_tickformat=".1e",
            xaxis_tickformat=".1e",
            xaxis_tickangle=-45,
            title=title,
            legend_title='solver',
        )

    else:
        plt.legend(fontsize=14)
        plt.xlabel(x_label, fontsize=14)
        plt.ylabel(f"{_remove_prefix(obj_col, 'objective_')}: {y_label}",
                   fontsize=14)
        plt.title(title, fontsize=14)
        plt.tight_layout()

    return fig


def plot_suboptimality_curve(df, obj_col='objective_value', plotly=False):
    """Plot suboptimality curve for a given benchmark and dataset.

    Plot suboptimality, that is F(x) - F(x^*) as a function of time,
    where F(x^*) is the smallest value reached in df.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.
    obj_col : str
        Column to select in the DataFrame for the plot.
    plotly : bool
        If set to True, output a plotly figure for HTML display.

    Returns
    -------
    fig : instance of matplotlib.figure.Figure
        The matplotlib figure.
    """
    return plot_objective_curve(df, obj_col=obj_col, plotly=plotly,
                                suboptimality=True)


def plot_relative_suboptimality_curve(df, obj_col='objective_value',
                                      plotly=False):
    """Plot relative suboptimality curve for a given benchmark and dataset.

    Plot relative suboptimality, that is (F(x) - F(x*)) / (F_0 - F(x*)) as a
    function of the time, where F(x*) is the smallest value reached in df and
    F_0 the largest initial loss across all solvers.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.
    obj_col : str
        Column to select in the DataFrame for the plot.
    plotly : bool
        If set to True, output a plotly figure for HTML display.

    Returns
    -------
    fig : instance of matplotlib.figure.Figure
        The matplotlib figure.
    """
    return plot_objective_curve(df, obj_col=obj_col, plotly=plotly,
                                suboptimality=True, relative=True)


def plot_iteration_suboptimality_curve(df, obj_col='objective_value',
                                       plotly=False):
    """Plot suboptimality curve for a given benchmark and dataset as a
    function of the stop_val.

    Plot suboptimality, that is F(x) - F(x^*) as a function of the stop_val,
    where F(x^*) is the smallest value reached in df.

    Note that this plot only makes sense if all solvers have been run with
    similar stopping strategy.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.
    obj_col : str
        Column to select in the DataFrame for the plot.
    plotly : bool
        If set to True, output a plotly figure for HTML display.

    Returns
    -------
    fig : instance of matplotlib.figure.Figure
        The matplotlib figure.
    """
    return plot_objective_curve(df, obj_col=obj_col, plotly=plotly,
                                suboptimality=True, iteration=True)


def plot_iteration_curve(df, obj_col='objective_value', plotly=False):
    """Plot objective for a given benchmark and dataset as a
    function of the stop_val.

    Note that this plot only makes sense if all solvers have been run with
    similar stopping strategy.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.
    obj_col : str
        Column to select in the DataFrame for the plot.
    plotly : bool
        If set to True, output a plotly figure for HTML display.

    Returns
    -------
    fig : instance of matplotlib.figure.Figure
        The matplotlib figure.
    """
    return plot_objective_curve(df, obj_col=obj_col, plotly=plotly,
                                iteration=True)
