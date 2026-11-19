r"""Create and run an R solver benchmark
====================================

This example shows how to add an R solver in a simple benchmark using
benchopt's helpers to call R code from Python.

The benchmark objective is a simple minimization task:

.. math::

    \min_{\hat{X}} \; \mathrm{MSE}(X, \hat{X})

We define:

- a Python ``Objective`` that evaluates MSE between ``X`` and ``X_hat``;
- a Python ``Dataset`` that generates a random matrix ``X``;
- two solvers:

  - ``Python-GD`` implemented in Python;
  - ``R-PGD`` implemented in R and called through ``rpy2``.

At the end, we run the benchmark and display the comparison.
"""

# Import example helpers to define the benchmark and
# programmatically call the CLI.
from benchopt.helpers.run_examples import ExampleBenchmark
from benchopt.helpers.run_examples import benchopt_cli
from benchopt.helpers.run_examples import EXAMPLES_ROOT


# %%
# First, we define the initial Python benchmark, based on the benchmark
# ``examples/minimal_benchmark``. It contains an ``objective.py`` file,
# a simulated dataset and a full python solver based on gradient descent.

benchmark = ExampleBenchmark(
    base="minimal_benchmark", name="r_solver",
    ignore=["custom_plot.py", "example_config.yml"]
)
benchmark

# %%
# We can now add a solver in R with the same algorithm.
# To do this, we create a new file ``r_pgd.py`` that defines a solver calling
# an R function via ``benchopt.helpers.r_lang`` and ``rpy2``.
#
# The R code is defined in a separate file ``r_pgd.R``, loaded from Python.

R_SOLVER = EXAMPLES_ROOT / "language_solvers" / "r_pgd.py"
R_SOLVER_PY = R_SOLVER.read_text(encoding="utf-8")
R_SOLVER_R = R_SOLVER.with_suffix(".R").read_text(encoding="utf-8")

benchmark.update(
    solvers={"r_pgd.py": R_SOLVER_PY, "r_pgd.R": R_SOLVER_R},
)

# %%
# To run this benchmark, we need to install solver dependencies.
# We use ``benchopt install`` with ``-s`` to select only this solver.
# If R is not available in your environment, this command can install it
# through conda using the solver requirements.

benchopt_cli(f"install {benchmark.benchmark_dir} -s r-pgd")

# %%
# Then, we can run the benchmark and show the comparison.

benchopt_cli(f"run {benchmark.benchmark_dir} -n 20 -r 4")

# %%
# Here, you should see that the R solver and Python solver obtain similar
# convergence profiles, with runtime differences depending on your setup.

# sphinx_gallery_thumbnail_number = -1
# sphinx_gallery_start_ignore
# Generate thumbnail for the sphinx gallery
benchopt_cli(
    f"plot {benchmark.benchmark_dir} --no-html --kind objective_curve"
)
# sphinx_gallery_end_ignore
