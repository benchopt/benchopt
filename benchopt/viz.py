# import numpy as np
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

    plt.figure(dataset_name)
    eps = 1e-10
    c_star = df.loss.min() - eps
    for m in solvers:
        df_ = df[df.solver == m]
        curve = df_.groupby('sample').median()
        plt.loglog(curve.time, curve.loss - c_star, label=m)
    plt.legend()
    plt.xlabel("Time [sec]")
    plt.ylabel(r"$F(\beta) - F(\beta^*)$")
    plt.tight_layout()
    plt.title(f"{benchmark_name}\nData: {dataset_name}")
    plt.savefig(f"output_benchmarks/{benchmark}_{dataset_name.lower()}.pdf")


def plot_histogram(df, benchmark, dataset_name):
    print("plotting histo!!!")

# def make_time_curve(df):
#     t_min = df.time.min()
#     t_max = df.time.max()
#     time = np.logspace(np.log10(t_min), np.log10(t_max), 20)
#     extended_time = np.r_[0, time, 2*t_max]
#     bins = np.c_[(extended_time[:-2] + time) / 2,
#                  (extended_time[2:] + time) / 2]
