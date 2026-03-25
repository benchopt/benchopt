r"""Create and run a Julia solver benchmark
=======================================

This example shows how to create a tiny benchmark from scratch and add a
solver implemented in Julia.

The benchmark objective is a simple reconstruction task:

.. math::

    \min_{\hat{X}} \; \mathrm{MSE}(X, \hat{X})

We define:

- a Python ``Objective`` that evaluates MSE between ``X`` and ``X_hat``;
- a Python ``Dataset`` that generates a random matrix ``X``;
- two solvers:

  - ``Python-GD`` implemented in Python;
  - ``Julia-GD`` implemented in Julia and called through ``JuliaSolver``.

At the end, we run the benchmark and display the comparison.
"""

# Import example benchmark helpers
from benchopt.helpers.run_examples import ExampleBenchmark
from benchopt.helpers.run_examples import benchopt_cli


# %%
# First, we define the initial Python benchmark, based on the benchmark
# ``examples/minimal_benchmark``. It contains an ``objective.py`` file,
# a simulated dataset and a full python solver based on gradient descent.

benchmark = ExampleBenchmark(
    base="minimal_benchmark", name="julia_solver",
    ignore=["custom_plot.py", "example_config.yml"]
)
benchmark

# %%
# Then add the Julia solver. The helper updates the temporary benchmark and
# displays the resulting files as tabs, including the Julia source file.

JULIA_SOLVER_PY = """
    from pathlib import Path

    from benchopt.helpers.julia import JuliaSolver
    from benchopt.helpers.julia import get_jl_interpreter


    JULIA_SOLVER_FILE = str(Path(__file__).with_suffix('.jl'))


    class Solver(JuliaSolver):
        name = "Julia-GD"
        sampling_strategy = "iteration"
        parameters = {"lr": [1e-3, 1e-2]}
        requirements = [
            "https://repo.prefix.dev/julia-forge::julia",
            "pip::julia",
        ]

        def set_objective(self, X):
            self.X = X
            jl = get_jl_interpreter()
            self.julia_gd = jl.include(JULIA_SOLVER_FILE)

        def warm_up(self):
            # Make sure we don't account for the Julia loading time in the
            # first iteration of the benchmark.
            self.julia_gd(self.X, self.lr, 20)

        def run(self, n_iter):
            # Here we cannot call a python callback, so we call iteratively
            # the solver with a growing number of iterations.
            self.X_hat = self.julia_gd(self.X, self.lr, n_iter)

        def get_result(self):
            return dict(X_hat=self.X_hat)
"""


JULIA_SOLVER_JL = """
    function gradient_descent(X, lr, n_iter)
        X_hat = zeros(size(X))
        for _ in 1:n_iter
            grad = X_hat - X
            X_hat -= lr * grad
        end
        return X_hat
    end
"""

benchmark.update(
    solvers={"julia_gd.py": JULIA_SOLVER_PY, "julia_gd.jl": JULIA_SOLVER_JL},
)

# %%
# To be able to run this benchmark, we use ``benchopt install`` to install our
# new solver dependencies. If Julia is not available in your environment,
# this command will use ``conda`` to install it.

benchopt_cli(f"install {benchmark.benchmark_dir} -s julia-gd")

# %%
# Then, we can run the benchmark and show the comparison.

benchopt_cli(f"run {benchmark.benchmark_dir} -n 20 -r 4")

# %%
# Here, you see that the Julia solver is faster than the Python one.
# You also notice that the first iteration seems to take much longer than the
# other, hinting to a loading time for the solver.
