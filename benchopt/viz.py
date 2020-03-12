import ctypes
import numpy as np
import matplotlib.pyplot as plt
from .config import get_benchmark_setting


def plot_benchmark(df, benchmark):

    plots = get_benchmark_setting(benchmark, 'plots')

    datasets = df.data.unique()
    for data in datasets:
        df_data = df[df.data == data]
        objectives = df.objective.unique()
        for objective in objectives:
            df_obj = df_data[df_data.objective == objective]
            if 'convergence_curve' in plots:
                plot_convergence_curve(df_obj, benchmark)
            if 'histogram' in plots:
                plot_histogram(df_obj, benchmark)
    plt.show()


def plot_convergence_curve(df, benchmark):
    dataset_name = df.data.unique()[0]
    objective_name = df.objective.unique()[0]
    plot_id = hash((benchmark, dataset_name, objective_name))
    plot_id = ctypes.c_size_t(plot_id).value

    solvers = df.solver.unique()

    plt.figure()
    eps = 1e-10
    c_star = df.obj.min() - eps
    for i, m in enumerate(solvers):
        df_ = df[df.solver == m]
        curve = df_.groupby('sample').median()
        q1 = df_.groupby('sample').time.quantile(.1)
        q9 = df_.groupby('sample').time.quantile(.9)
        plt.loglog(curve.time, curve.obj - c_star, f"C{i}", label=m,
                   linewidth=3)
        plt.fill_betweenx(curve.obj - c_star, q1, q9, color=f"C{i}", alpha=.3)
    xlim = plt.xlim()
    plt.hlines(eps, *xlim, color='k', linestyle='--')
    plt.xlim(xlim)
    plt.legend()
    plt.xlabel("Time [sec]", fontsize=18)
    plt.ylabel(r"F(x) - F(x*)", fontsize=18)
    plt.title(f"{objective_name}\nData: {dataset_name}", fontsize=18)
    plt.tight_layout()
    plt.savefig(f"output_benchmarks/convergence_{plot_id}.pdf")


def plot_histogram(df, benchmark):
    dataset_name = df.data.unique()[0]
    objective_name = df.objective.unique()[0]
    plot_id = hash((benchmark, dataset_name, objective_name))
    plot_id = ctypes.c_size_t(plot_id).value

    solvers = df.solver.unique()

    n_solvers = len(solvers)

    eps = 1e-6
    width = 1 / (n_solvers + 2)
    colors = color_palette(n_solvers)

    rect_list = []
    ticks_list = []
    fig = plt.figure()
    ax = fig.gca()
    c_star = df.obj.min() + eps
    for i, solver_name in enumerate(solvers):
        xi = (i + 1.5) * width
        ticks_list.append((xi, solver_name))
        df_ = df[df.solver == solver_name]

        # Find the first sample which reach a given tolerance
        df_tol = df_.groupby('sample').filter(
            lambda x: x.obj.max() < c_star)
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
    plt.title(f"{objective_name}\nData: {dataset_name}", fontsize=12)
    plt.tight_layout()
    plt.savefig(f"output_benchmarks/histogram_{plot_id}.pdf")

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
