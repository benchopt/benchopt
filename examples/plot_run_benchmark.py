"""
===========================
Run benchmark from a script
===========================

"""

import os
from pathlib import Path
import matplotlib.pyplot as plt
from benchopt import run_benchmark
from benchopt.viz import plot_benchmark, PLOT_KINDS


BENCHMARK_PATH = Path(os.getcwd()).parent / 'benchmarks' / 'logreg_l2'


try:
    df = run_benchmark(
        str(BENCHMARK_PATH), ['sklearn', 'lightning'],
        dataset_names=['Simulated*n_samples=200,n_features=500*'],
        max_runs=100, timeout=20, n_repetitions=3,
        plot_result=False, show_progress=False
    )
except RuntimeError:
    raise RuntimeError(
        "This example can only work when Lasso benchmark is cloned in the "
        "example folder. Please run:\n"
        "$ git clone https://github.com/benchopt/benchmark_logreg_l2 "
        f"{BENCHMARK_PATH.resolve()}"
    )


kinds = list(PLOT_KINDS.keys())
figs = plot_benchmark(df, benchmark=str(BENCHMARK_PATH), kinds=kinds)
plt.show()
