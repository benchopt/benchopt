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

os.chdir(Path(os.path.dirname(benchopt.__file__)) / '..')

df = run_benchmark('logreg_l2', ['sklearn'], forced_solvers=[],
                   dataset_names=['simulated'],
                   max_samples=100, timeout=20, n_rep=3)

figs = plot_benchmark(df, benchmark='logreg_l2')
plt.show()
