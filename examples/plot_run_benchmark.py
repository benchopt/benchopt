"""
===========================
Run benchmark from a script
===========================

"""

from pathlib import Path
import matplotlib.pyplot as plt
from benchopt import run_benchmark
from benchopt.benchmark import Benchmark
from benchopt.plotting import plot_benchmark, PLOT_KINDS


BENCHMARK_PATH = (
    Path().resolve().parent / 'benchmarks' / 'benchmark_logreg_l2'
)


try:
    save_file = run_benchmark(
        Benchmark(BENCHMARK_PATH), ['sklearn[liblinear]', 'sklearn[newton-cg]',
                                    'lightning'],
        dataset_names=['Simulated*[n_features=500,n_samples=200]'],
        objective_filters=['L2 Logistic Regression[lmbd=1.0]'],
        max_runs=100, timeout=20, n_repetitions=15,
        plot_result=False, show_progress=True
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
