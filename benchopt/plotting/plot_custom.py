import matplotlib.pyplot as plt


def plot_custom(df, plot_func):
    """Plot objective curve for a given benchmark and dataset.

    Plot the objective value F(x) as a function of the time.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.
    obj_col : str
        Column to select in the DataFrame for the plot.
    suboptimality : bool
        If set to True, remove the optimal objective value F(x^*). Here the
        value of F(x^*) is taken as the smallest value reached across all
        solvers.
    relative : bool
        If set to True, scale the objective value by 1 / F_0 where F_0 is
        computed as the largest objective value accross all initialization.

    Returns
    -------
    fig : matplotlib.Figure
        The rendered figure.
    """

    fig = plt.figure()

    return fig
