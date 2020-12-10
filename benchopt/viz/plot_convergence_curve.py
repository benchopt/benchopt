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
        The matplotlib figure of the objective values.
    """
    solver_names = df['solver_name'].unique()
    dataset_name = df['data_name'].unique()[0]
    objective_name = df['objective_name'].unique()[0]

    fig = plt.figure()
    eps = 1e-10
    c_star = df['objective_value'].min() - eps
    for i, solver_name in enumerate(solver_names):
        df_ = df[df['solver_name'] == solver_name]
        curve = df_.groupby('stop_val').median()
        q1 = df_.groupby('stop_val')['time'].quantile(.1)
        q9 = df_.groupby('stop_val')['time'].quantile(.9)
        plt.loglog(curve['time'], curve['objective_value'] - c_star, f"C{i}",
                   label=solver_name, linewidth=3)
        plt.fill_betweenx(curve['objective_value'] - c_star, q1, q9,
                          color=f"C{i}", alpha=.3)
    xlim = plt.xlim()
    plt.hlines(eps, *xlim, color='k', linestyle='--')
    plt.xlim(xlim)
    plt.legend(fontsize=14)
    plt.xlabel("Time [sec]", fontsize=14)
    plt.ylabel(r"F(x) - F(x*)", fontsize=14)
    plt.title(f"{objective_name}\nData: {dataset_name}", fontsize=14)
    plt.tight_layout()
    return fig
