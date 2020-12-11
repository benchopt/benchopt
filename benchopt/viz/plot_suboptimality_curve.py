import matplotlib.pyplot as plt


def plot_suboptimality_curve(df, benchmark, relative=False):
    """Plot suboptimality curve for a given benchmark and dataset.

    Plot suboptimality if relative == False, that is
    F(x) - F(x*) as a function of x

    Plot relative suboptimality if relative == True, that is
    (F(x) - F(x*)) / (F_0 - F(x*)) as a function of x
    with F(x*) is the smallest value reached in df and
    F_0 the largest initial loss across all solvers.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.
    benchmark : str
        The path to the benchmark folder.

    Returns
    -------
    fig : instance of matplotlib.figure.Figure
        The matplotlib figure.
    """
    solver_names = df['solver_name'].unique()
    dataset_name = df['data_name'].unique()[0]
    objective_name = df['objective_name'].unique()[0]

    fig = plt.figure()
    eps = 1e-10
    c_star = df['objective_value'].min() - eps
    max_f_0 = df[df['stop_val'] == 1]['objective_value'].max()
    for i, solver_name in enumerate(solver_names):
        df_ = df[df['solver_name'] == solver_name]
        curve = df_.groupby('stop_val').median()
        q1 = df_.groupby('stop_val')['time'].quantile(.1)
        q9 = df_.groupby('stop_val')['time'].quantile(.9)

        if relative:
            y_label = r"$\frac{F(x) - F(x*)}{F(x^0) - F(x*)}$"
            y_axis = (curve['objective_value'] - c_star) / (max_f_0 - c_star)
        else:
            y_label = r"$F(x) - F(x*)$"
            y_axis = curve['objective_value'] - c_star
        plt.loglog(curve['time'], y_axis, f"C{i}",
                   label=solver_name, linewidth=3)
        plt.fill_betweenx(y_axis, q1, q9,
                          color=f"C{i}", alpha=.3)
    xlim = plt.xlim()
    plt.hlines(eps, *xlim, color='k', linestyle='--')
    plt.xlim(xlim)
    plt.legend(fontsize=14)
    plt.xlabel("Time [sec]", fontsize=14)
    plt.ylabel(y_label, fontsize=14)
    plt.title(f"{objective_name}\nData: {dataset_name}", fontsize=14)
    plt.tight_layout()
    return fig


def plot_relative_suboptimality_curve(df, benchmark):
    """Plot relative suboptimality curve for a given benchmark and dataset.

    Plot relative suboptimality if relative == True, that is
    (F(x) - F(x*)) / (F_0 - F(x*)) as a function of x
    with F(x*) is the smallest value reached in df and
    F_0 the largest initial loss across all solvers.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.
    benchmark : str
        The path to the benchmark folder.

    Returns
    -------
    fig : instance of matplotlib.figure.Figure
        The matplotlib figure.
    """
    return plot_suboptimality_curve(df, benchmark, relative=True)
