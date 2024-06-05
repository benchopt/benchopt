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
from benchopt.plotting.plot_objective_curve import reset_solver_styles_idx


BENCHMARK_PATH = (
    Path().resolve().parent / 'benchmarks' / 'benchmark_logreg_l2'
)


try:

    benchmark = Benchmark(BENCHMARK_PATH)

    solvers = benchmark.check_solver_patterns(
        ['sklearn[liblinear]', 'sklearn[newton-cg]', 'lightning']
    )
    datasets = benchmark.check_dataset_patterns(
        ["Simulated[n_features=500,n_samples=200]"]
    )
    objectives = benchmark.check_objective_filters(
        ['L2 Logistic Regression[lmbd=1.0]']
    )

    save_file = run_benchmark(
        benchmark, solvers=solvers, datasets=datasets, objectives=objectives,
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
reset_solver_styles_idx()
figs = plot_benchmark(save_file, benchmark=Benchmark(BENCHMARK_PATH),
                      kinds=kinds, html=False)
plt.show()
