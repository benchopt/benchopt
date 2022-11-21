import matplotlib.pyplot as plt

CMAP = plt.get_cmap('tab20')
COLORS = [CMAP(i) for i in range(CMAP.N)]
COLORS = COLORS[::2] + COLORS[1::2]
MARKERS = {i: v for i, v in enumerate(plt.Line2D.markers)}


solvers_idx = {}


def _remove_prefix(text, prefix):
    return text[len(prefix):] if text.startswith(prefix) else text


def plot_objective_curve(df, obj_col='objective_value',
                         suboptimality=False, relative=False):
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

    df = df.copy()
    solver_names = df['solver_name'].unique()
    dataset_name = df['data_name'].unique()[0]
    objective_name = df['objective_name'].unique()[0]
    title = f"{objective_name}\nData: {dataset_name}"
    df.query(f"`{obj_col}` not in [inf, -inf]", inplace=True)
    y_label = "F(x)"
    if suboptimality:
        eps = 1e-10
        y_label = "F(x) - F(x*)"
        c_star = df[obj_col].min() - eps
        df.loc[:, obj_col] -= c_star

    if relative:
        if suboptimality:
            y_label = "F(x) - F(x*) / F(x0) - F(x*)"
        else:
            y_label = "F(x) / F(x0)"
        max_f_0 = df[df['stop_val'] == 1][obj_col].max()
        df.loc[:, obj_col] /= max_f_0

    fig = plt.figure()

    if df[obj_col].count() == 0:  # missing values
        plt.text(0.5, 0.5, "Not Available")
        return fig

    for i, solver_name in enumerate(solver_names):
        df_ = df[df['solver_name'] == solver_name]
        curve = df_.groupby('stop_val').median(numeric_only=True)

        q1 = df_.groupby('stop_val')['time'].quantile(.1)
        q9 = df_.groupby('stop_val')['time'].quantile(.9)

        color, marker = get_solver_style(solver_name, plotly=False)
        plt.loglog(curve['time'], curve[obj_col], color=color, marker=marker,
                   label=solver_name, linewidth=3)
        plt.fill_betweenx(curve[obj_col], q1, q9, color=color, alpha=.3)

    if suboptimality and not relative:
        plt.hlines(eps, df['time'].min(), df['time'].max(), color='k',
                   linestyle='--')
        plt.xlim(df['time'].min(), df['time'].max())

    # Format the plot to be nice
    plt.legend(fontsize=14)
    plt.xlabel("Time [sec]", fontsize=14)
    plt.ylabel(f"{_remove_prefix(obj_col, 'objective_')}: {y_label}",
               fontsize=14)
    plt.title(title, fontsize=14)
    plt.tight_layout()

    return fig


def plot_suboptimality_curve(df, obj_col='objective_value'):
    """Plot suboptimality curve for a given benchmark and dataset.

    Plot suboptimality, that is F(x) - F(x^*) as a function of time,
    where F(x^*) is the smallest value reached in df.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.
    obj_col : str
        Column to select in the DataFrame for the plot.

    Returns
    -------
    fig : instance of matplotlib.figure.Figure
        The matplotlib figure.
    """
    return plot_objective_curve(df, obj_col=obj_col, suboptimality=True)


def plot_relative_suboptimality_curve(df, obj_col='objective_value'):
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

    Returns
    -------
    fig : instance of matplotlib.figure.Figure
        The matplotlib figure.
    """
    return plot_objective_curve(df, obj_col=obj_col, suboptimality=True,
                                relative=True)


def compute_quantiles(df_filtered):
    q1 = df_filtered.groupby('stop_val')['time'].quantile(.1)
    q9 = df_filtered.groupby('stop_val')['time'].quantile(.9)

    return q1, q9


def get_solver_style(solver, plotly=True):
    idx = solvers_idx.get(solver, len(solvers_idx))
    solvers_idx[solver] = idx

    color = COLORS[idx % len(COLORS)]
    marker = MARKERS[idx % len(MARKERS)]

    if plotly:
        color = tuple(255*x if i != 3 else x for i, x in enumerate(color))
        color = f'rgba{color}'
        marker = idx

    return color, marker
