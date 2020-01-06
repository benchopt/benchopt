import numpy as np
import matplotlib.pyplot as plt
from .config import get_benchmark_setting


def plot_benchmark(df, benchmark):

    plots = get_benchmark_setting(benchmark, 'plots')

    datasets = df.data.unique()
    for data in datasets:
        df_data = df[df.data == data]
        if 'convergence_curve' in plots:
            plot_convergence_curve(df_data, benchmark, data)
        if 'histogram' in plots:
            plot_histogram(df_data, benchmark, data)
    plt.show()


def plot_convergence_curve(df, benchmark, dataset_name):

    benchmark_name = get_benchmark_setting(benchmark, 'name')
    solvers = df.solver.unique()

    plt.figure(f"{dataset_name} - Convergence")
    eps = 1e-10
    c_star = df.objective.min() - eps
    for m in solvers:
        df_ = df[df.solver == m]
        curve = df_.groupby('sample').median()
        plt.loglog(curve.time, curve.objective - c_star, label=m)
    xlim = plt.xlim()
    plt.hlines(eps, *xlim, color='k', linestyle='--')
    plt.xlim(xlim)
    plt.legend()
    plt.xlabel("Time [sec]")
    plt.ylabel(r"$F(\beta) - F(\beta^*)$")
    plt.title(f"{benchmark_name}\nData: {dataset_name}")
    plt.tight_layout()
    plt.savefig(f"output_benchmarks/{benchmark}_{dataset_name.lower()}"
                "_convergence.pdf")


def plot_histogram(df, benchmark, dataset_name):

    benchmark_name = get_benchmark_setting(benchmark, 'name')
    solvers = df.solver.unique()

    n_solvers = len(solvers)

    eps = 1e-6
    width = 1 / (n_solvers + 2)
    colors = color_palette(n_solvers)

    rect_list = []
    ticks_list = []
    fig = plt.figure(f"{dataset_name} - Histogram")
    ax = fig.gca()
    c_star = df.objective.min() + eps
    for i, solver_name in enumerate(solvers):
        xi = (i + 1.5) * width
        ticks_list.append((xi, solver_name))
        df_ = df[df.solver == solver_name]

        # Find the first sample which reach a given tolerance
        df_tol = df_.groupby('sample').filter(
            lambda x: x.objective.max() < c_star)
        if df_tol.empty:
            print(f"Solver {solver_name} did not reach precision {eps}.")
            height = df.time.max()
            rect = ax.bar(
                x=xi, height=height, width=width, color='w', edgecolor='k')
            ax.annotate("Did not converged", xy=(xi, height/2), ha='center',
                        va='center', color='k', rotation=90)
            rect_list.append(rect)
            continue
        sample = df_tol['sample'].min()
        this_df = df_[df_['sample'] == sample]
        rect_list.append(ax.bar(
            x=xi, height=this_df.time.mean(), width=width, color=colors[i]))

        plt.scatter(np.ones_like(this_df.time) * xi, this_df.time,
                    marker='_', color='k', zorder=10)

    ax.set_xticks([xi for xi, _ in ticks_list])
    ax.set_xticklabels([label for _, label in ticks_list], rotation=60)
    ax.set_yscale('log')
    plt.xlim(0, 1)
    plt.ylabel("Time [sec]")
    plt.title(f"{benchmark_name}\nData: {dataset_name}")
    plt.tight_layout()
    plt.savefig(f"output_benchmarks/{benchmark}_{dataset_name.lower()}"
                "_histogram.pdf")

# def make_time_curve(df):
#     t_min = df.time.min()
#     t_max = df.time.max()
#     time = np.logspace(np.log10(t_min), np.log10(t_max), 20)
#     extended_time = np.r_[0, time, 2*t_max]
#     bins = np.c_[(extended_time[:-2] + time) / 2,
#                  (extended_time[2:] + time) / 2]


def color_palette(n_colors=4, cmap='viridis', extrema=False):
    """Create a color palette from a matplotlib color map"""
    if extrema:
        bins = np.linspace(0, 1, n_colors)
    else:
        bins = np.linspace(0, 1, n_colors * 2 - 1 + 2)[1:-1:2]

    cmap = plt.get_cmap(cmap)
    palette = list(map(tuple, cmap(bins)[:, :3]))
    return palette
