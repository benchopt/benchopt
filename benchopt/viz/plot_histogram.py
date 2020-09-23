import numpy as np
import matplotlib.pyplot as plt

from .helpers import _color_palette


def plot_histogram(df, benchmark):
    """Plot histogram for a given benchmark and dataset.

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

    n_solvers = len(solvers)

    eps = 1e-6
    width = 1 / (n_solvers + 2)
    colors = _color_palette(n_solvers)

    rect_list = []
    ticks_list = []
    fig = plt.figure()
    ax = fig.gca()
    c_star = df.obj.min() + eps
    for i, solver_name in enumerate(solvers):
        xi = (i + 1.5) * width
        ticks_list.append((xi, solver_name))
        df_ = df[df.solver == solver_name]

        # Find the first stop_val which reach a given tolerance
        df_tol = df_.groupby('stop_val').filter(
            lambda x: x.obj.max() < c_star)
        if df_tol.empty:
            print(f"Solver {solver_name} did not reach precision {eps}.")
            height = df.time.max()
            rect = ax.bar(
                x=xi, height=height, width=width, color='w', edgecolor='k')
            ax.annotate("Did not converge", xy=(xi, height/2), ha='center',
                        va='center', color='k', rotation=90)
            rect_list.append(rect)
            continue
        stop_val = df_tol['stop_val'].min()
        this_df = df_[df_['stop_val'] == stop_val]
        rect_list.append(ax.bar(
            x=xi, height=this_df.time.mean(), width=width, color=colors[i]))

        plt.scatter(np.ones_like(this_df.time) * xi, this_df.time,
                    marker='_', color='k', zorder=10)

    ax.set_xticks([xi for xi, _ in ticks_list])
    ax.set_xticklabels([label for _, label in ticks_list], rotation=60)
    ax.set_yscale('log')
    plt.xlim(0, 1)
    plt.ylabel("Time [sec]")
    plt.title(f"{objective_name}\nData: {dataset_name}", fontsize=12)
    plt.tight_layout()
    return fig
