"""
===========================
Run benchmark from a script
===========================

"""

import os
import matplotlib.pyplot as plt
from benchopt import run_benchmark
from benchopt.viz import plot_benchmark

try:
    df = run_benchmark(
        'benchmark_logreg_l2', ['sklearn', 'lightning'],
        dataset_names=['Simulated*n_samples=200,n_features=500*'],
        max_runs=100, timeout=20, n_repetitions=3,
        plot_result=False, show_progress=False
    )
except RuntimeError:
    examples = os.getcwd()
    raise RuntimeError(
        "This example can only work when Lasso benchmark is cloned in the "
        "example folder. Please run:\n"
        "$ git clone https://github.com/benchopt/benchmark_logreg_l2 "
        f"{examples}/benchmark_logreg_l2"
    )


figs = plot_benchmark(df, benchmark='benchmark_logreg_l2')
plt.show()
