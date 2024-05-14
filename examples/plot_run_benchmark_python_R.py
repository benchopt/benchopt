"""
============================
Demo benchmark with R/Python
============================

"""

from pathlib import Path
import matplotlib.pyplot as plt
from benchopt import run_benchmark
from benchopt.benchmark import Benchmark
from benchopt.plotting import plot_benchmark, PLOT_KINDS
from benchopt.plotting.plot_objective_curve import reset_solver_styles_idx


BENCHMARK_PATH = Path().resolve().parent / 'benchmarks' / 'benchmark_lasso'

if not BENCHMARK_PATH.exists():
    raise RuntimeError(
        "This example can only work when Lasso benchmark is cloned in the "
        "example folder. Please run:\n"
        "$ git clone https://github.com/benchopt/benchmark_lasso "
        f"{BENCHMARK_PATH.resolve()}"
    )

benchmark = Benchmark(BENCHMARK_PATH)

solvers = benchmark.check_solver_patterns(
    ['Python-PGD[use_acceleration=False]', 'R-PGD']
)
datasets = benchmark.check_dataset_patterns(
    ["Simulated[n_features=5000,n_samples=100,rho=0]"]
)
objectives = benchmark.check_objective_filters(
    ['*[fit_intercept=False,reg=0.5]']
)

save_file = run_benchmark(
    benchmark, solvers=solvers, datasets=datasets, objectives=objectives,
    max_runs=100, timeout=100, n_repetitions=5,
    plot_result=False, show_progress=False
)


kinds = list(PLOT_KINDS.keys())
reset_solver_styles_idx()
figs = plot_benchmark(
    save_file, benchmark=Benchmark(BENCHMARK_PATH), kinds=kinds, html=False
)
plt.show()
