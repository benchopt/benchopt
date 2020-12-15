import matplotlib.pyplot as plt


def plot_objective_curve(df):
    """Plot objective curve for a given benchmark and dataset.

    F(x) as a function of x.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.

    Returns
    -------
    fig : instance of matplotlib.figure.Figure
        The matplotlib figure of the objective values.
    """
    solver_names = df['solver_name'].unique()
    dataset_name = df['data_name'].unique()[0]
    objective_name = df['objective_name'].unique()[0]

    fig = plt.figure()
    for i, solver_name in enumerate(solver_names):
        df_ = df[df['solver_name'] == solver_name]
        curve = df_.groupby('stop_val').median()
        q1 = df_.groupby('stop_val')['time'].quantile(.1)
        q9 = df_.groupby('stop_val')['time'].quantile(.9)
        plt.loglog(curve['time'], curve['objective_value'], f"C{i}",
                   label=solver_name, linewidth=3)
        plt.fill_betweenx(curve['objective_value'], q1, q9,
                          color=f"C{i}", alpha=.3)
    xlim = plt.xlim()
    plt.xlim(xlim)
    plt.legend(fontsize=14)
    plt.xlabel("Time [sec]", fontsize=14)
    plt.ylabel(r"$F(x)$", fontsize=14)
    plt.title(f"{objective_name}\nData: {dataset_name}", fontsize=14)
    plt.tight_layout()
    return fig
