import matplotlib.pyplot as plt

from .helpers_compat import get_figure
from .helpers_compat import add_h_line
from .helpers_compat import fill_between_x

CMAP = plt.get_cmap('tab20')


def plot_objective_curve(df, plotly=False, suboptimality=False,
                         relative=False):
    """Plot objective curve for a given benchmark and dataset.

    Plot the objective value F(x) as a function of the time.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.
    plotly : bool
        If set to True, output a plotly figure for HTML display.
    suboptimality : bool
        If set to True, remove the optimal objective value F(x^*). Here the
        value of F(x^*) is taken as the smallest value reached across all
        solvers.
    relative : bool
        If set to True, scale the objective value by 1 / F_0 where F_0 is
        computed as the largest objective value accross all initialization.

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

    y_label = r"$F(x)$"
    if suboptimality:
        eps = 1e-10
        y_label = r"$F(x) - F(x*)$"
        c_star = df['objective_value'].min() - eps
        df['objective_value'] -= c_star

    if relative:
        obj = y_label[1:-1]
        y_label = r"$\frac{{{num}}}{{{den}}}$".format(
            num=obj, den=obj.replace('F(x)', 'F(x^0)')
        )
        max_f_0 = df[df['stop_val'] == 1]['objective_value'].max()
        df['objective_value'] /= max_f_0

    fig = get_figure(plotly)
    for i, solver_name in enumerate(solver_names):
        df_ = df[df['solver_name'] == solver_name]
        curve = df_.groupby('stop_val').median()

        q1 = df_.groupby('stop_val')['time'].quantile(.1)
        q9 = df_.groupby('stop_val')['time'].quantile(.9)

        fill_between_x(
            fig, curve['time'], q1, q9, curve['objective_value'],
            color=CMAP(i), marker=markers[i], label=solver_name, plotly=plotly
        )

    if suboptimality:
        add_h_line(fig, eps, [df['time'].min(), df['time'].max()],
                   plotly=plotly)

    # Format the plot to be nice
    if plotly:
        fig.update_layout(
            xaxis_type='log',
            yaxis_type='log',
            xaxis_title=r"Time [sec]",
            yaxis_title=y_label,
            yaxis_tickformat=".1e",
            xaxis_tickformat=".0e",
            xaxis_tickangle=-45,
            title=title,
            legend_title='solver'
        )
    else:
        plt.legend(fontsize=14)
        plt.xlabel("Time [sec]", fontsize=14)
        plt.ylabel(y_label, fontsize=14)
        plt.title(title, fontsize=14)
        plt.tight_layout()

    return fig


def plot_suboptimality_curve(df, plotly=False):
    """Plot suboptimality curve for a given benchmark and dataset.

    Plot suboptimality, that is F(x) - F(x*) as a function of time,
    where F(x*) is the smallest value reached in df.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.
    plotly : bool
        If set to True, output a plotly figure for HTML display.

    Returns
    -------
    fig : instance of matplotlib.figure.Figure
        The matplotlib figure.
    """
    return plot_objective_curve(df, plotly=plotly, suboptimality=True)


def plot_relative_suboptimality_curve(df, plotly=False):
    """Plot relative suboptimality curve for a given benchmark and dataset.

    Plot relative suboptimality, that is (F(x) - F(x*)) / (F_0 - F(x*)) as a
    function of the time, where F(x*) is the smallest value reached in df and
    F_0 the largest initial loss across all solvers.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.
    plotly : bool
        If set to True, output a plotly figure for HTML display.

    Returns
    -------
    fig : instance of matplotlib.figure.Figure
        The matplotlib figure.
    """
    return plot_objective_curve(df, plotly=plotly, suboptimality=True,
                                relative=True)
