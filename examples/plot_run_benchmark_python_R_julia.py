"""
==================================
Demo benchmark with Julia/R/Python
==================================

"""

import os
from pathlib import Path
import matplotlib.pyplot as plt
import benchopt
from benchopt import run_benchmark
from benchopt.viz import plot_benchmark

cwd = os.getcwd()
os.chdir(Path(os.path.dirname(benchopt.__file__)) / '..')

df = run_benchmark('benchmarks/lasso',
                   ['Python-PGD', 'R-PGD', 'Julia-PGD'],
                   forced_solvers=[],
                   dataset_names=['Simulated*n_samples=100,n_features=500*'],
                   max_runs=100, timeout=20, n_repetitions=3)

figs = plot_benchmark(df, benchmark='benchmarks/lasso')

plt.show()
os.chdir(cwd)
