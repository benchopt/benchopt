"""
===========================
Run benchmark from a script
===========================

"""

import os
from pathlib import Path
import matplotlib.pyplot as plt
from benchopt import run_benchmark
from benchopt.benchmark import Benchmark
from benchopt.plotting import plot_benchmark, PLOT_KINDS


BENCHMARK_PATH = Path(os.getcwd()).parent / 'benchmarks' / 'logreg_l2'


try:
    save_file = run_benchmark(
        Benchmark(BENCHMARK_PATH), ['sklearn', 'lightning'],
        dataset_names=['Simulated*n_samples=200,n_features=500*'],
        max_runs=100, timeout=20, n_repetitions=3,
        plot_result=False, show_progress=False
    )
except RuntimeError:
    raise RuntimeError(
        "This example can only work when Logreg-l2 benchmark is cloned in a "
        "`benchmarks` folder. Please run:\n"
        "$ git clone https://github.com/benchopt/benchmark_logreg_l2 "
        f"{BENCHMARK_PATH.resolve()}"
    )


kinds = list(PLOT_KINDS.keys())
figs = plot_benchmark(save_file, benchmark=Benchmark(BENCHMARK_PATH),
                      kinds=kinds, html=False)
plt.show()
