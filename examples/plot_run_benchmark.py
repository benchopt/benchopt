"""
===========================
Run benchmark from a script
===========================

"""

import os
from pathlib import Path
import matplotlib.pyplot as plt
import benchopt
from benchopt import run_benchmark
from benchopt.viz import plot_benchmark

cwd = os.getcwd()
os.chdir(Path(os.path.dirname(benchopt.__file__)) / '..')

df = run_benchmark('benchmarks/logreg_l2', ['sklearn', 'lightning'],
                   forced_solvers=[],
                   dataset_names=['Simulated*n_samples=200,n_features=500*'],
                   max_runs=100, timeout=20, n_repetitions=3)

figs = plot_benchmark(df, benchmark='benchmarks/logreg_l2')
plt.show()
os.chdir(cwd)
