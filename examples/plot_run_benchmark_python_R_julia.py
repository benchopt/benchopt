"""
==================================
Demo benchmark with Julia/R/Python
==================================

"""

import os
from pathlib import Path
import matplotlib.pyplot as plt
from benchopt import run_benchmark
from benchopt.viz import plot_benchmark


BENCHMARK_PATH = Path(os.getcwd()).parent / 'benchmarks' / 'lasso'

try:
    df = run_benchmark(
        str(BENCHMARK_PATH),
        ['Python-PGD*use_acceleration=False', 'R-PGD', 'Julia-PGD'],
        dataset_names=['Simulated*n_samples=100,n_features=500*'],
        objective_filters=['reg=0.5'],
        max_runs=100, timeout=100, n_repetitions=5,
        plot_result=False, show_progress=False
    )
except RuntimeError:
    raise RuntimeError(
        "This example can only work when Lasso benchmark is cloned in the "
        "example folder. Please run:\n"
        "$ git clone https://github.com/benchopt/benchmark_lasso "
        f"{BENCHMARK_PATH.resolve()}"
    )

figs = plot_benchmark(df, benchmark=str(BENCHMARK_PATH))
plt.show()
