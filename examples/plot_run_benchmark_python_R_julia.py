"""
==================================
Demo benchmark with Julia/R/Python
==================================

"""

import os
import matplotlib.pyplot as plt
from benchopt import run_benchmark
from benchopt.viz import plot_benchmark

try:
    df = run_benchmark(
        'benchmark_lasso',
        ['Python-PGD*use_acceleration=False', 'R-PGD', 'Julia-PGD'],
        dataset_names=['Simulated*n_samples=100,n_features=500*'],
        objective_filters=['reg=0.5'],
        max_runs=100, timeout=100, n_repetitions=5,
        plot_result=False, show_progress=False
    )
except RuntimeError:
    examples = os.getcwd()
    raise RuntimeError(
        "This example can only work when Lasso benchmark is cloned in the "
        "example folder. Please run:\n"
        "$ git clone https://github.com/benchopt/benchmark_lasso "
        f"{examples}/benchmark_lasso"
    )

figs = plot_benchmark(df, benchmark='benchmark_lasso')

plt.show()
