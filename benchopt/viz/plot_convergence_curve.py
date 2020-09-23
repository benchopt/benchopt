import matplotlib.pyplot as plt


def plot_convergence_curve(df, benchmark):
    """Plot convergence curve for a given benchmark and dataset.

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
    dataset_name = df.data.unique()[0]
    objective_name = df.objective.unique()[0]

    solvers = df.solver.unique()

    fig = plt.figure()
    eps = 1e-10
    c_star = df.obj.min() - eps
    for i, m in enumerate(solvers):
        df_ = df[df.solver == m]
        curve = df_.groupby('stop_val').median()
        q1 = df_.groupby('stop_val').time.quantile(.1)
        q9 = df_.groupby('stop_val').time.quantile(.9)
        plt.loglog(curve.time, curve.obj - c_star, f"C{i}", label=m,
                   linewidth=3)
        plt.fill_betweenx(curve.obj - c_star, q1, q9, color=f"C{i}", alpha=.3)
    xlim = plt.xlim()
    plt.hlines(eps, *xlim, color='k', linestyle='--')
    plt.xlim(xlim)
    plt.legend(fontsize=14)
    plt.xlabel("Time [sec]", fontsize=14)
    plt.ylabel(r"F(x) - F(x*)", fontsize=14)
    plt.title(f"{objective_name}\nData: {dataset_name}", fontsize=14)
    plt.tight_layout()
    return fig
