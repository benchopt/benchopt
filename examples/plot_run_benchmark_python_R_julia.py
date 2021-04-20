"""
==================================
Demo benchmark with Julia/R/Python
==================================

"""

import os
from pathlib import Path
import matplotlib.pyplot as plt
from benchopt import run_benchmark
from benchopt.benchmark import Benchmark
from benchopt.tests import SELECT_ONE_SIMULATED
from benchopt.plotting import plot_benchmark, PLOT_KINDS


BENCHMARK_PATH = Path(os.getcwd()).parent / 'benchmarks' / 'lasso'

try:
    save_file = run_benchmark(
        Benchmark(BENCHMARK_PATH),
        ['Python-PGD[^-]*use_acceleration=False', 'R-PGD', 'Julia-PGD'],
        dataset_names=[SELECT_ONE_SIMULATED],
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

kinds = list(PLOT_KINDS.keys())
figs = plot_benchmark(save_file, benchmark=Benchmark(BENCHMARK_PATH),
                      kinds=kinds, html=False)
plt.show()
