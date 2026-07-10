r"""Create and run a Julia solver benchmark
=======================================

This example shows how to add a Julia solver in a simple benchmark using
benchopt's helpers to call Julia code from Python.

The benchmark objective is a simple minimization task:

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
    base="minimal_benchmark", name="julia_solver",
    ignore=["custom_plot.py", "example_config.yml"]
)
benchmark

# %%
# We can now add solver in Julia with the same algorithm.
# To do this, we create a new file ``julia_gd.py`` that defines a solver based
# on the ``JuliaSolver`` class. This class provides helpers to call Julia code
# from Python, and to define the dependencies of the solver.
# The Julia code is defined in a separate file ``julia_gd.jl``, that is loaded
# and called from the Python solver.

JULIA_SOLVER = EXAMPLES_ROOT / "language_solvers" / "julia_gd.py"
JULIA_SOLVER_PY = JULIA_SOLVER.read_text(encoding="utf-8")
JULIA_SOLVER_JL = JULIA_SOLVER.with_suffix(".jl").read_text(encoding="utf-8")

benchmark.update(
    solvers={"julia_gd.py": JULIA_SOLVER_PY, "julia_gd.jl": JULIA_SOLVER_JL},
)

# %%
# In order to load the Julia interpreter, we use ``get_jl_interpreter``. This
# function returns a ``Julia`` object from ``PyJulia``, that can be used to
# interact with Julia. In particular, we can use the ``include`` method to load
# a Julia file and retrieve the functions defined in it as attributes of the
# returned object.
#
# Note that the Julia solver cannot call a Python callback to report
# intermediate results, so we call iteratively the Julia solver with a growing
# number of iterations to be able to report the curve of the convergence.

# %%
# To be able to run this benchmark, we need to install its dependencies. We can
# do this with ``benchopt install``, using with the ``-s`` option which allow
# to select only this solver if multiple solvers are present. If Julia is not
# available in your environment, this command will use ``conda`` to install it.

benchopt_cli(f"install {benchmark.benchmark_dir} -s julia-gd")

# %%
# Then, we can run the benchmark and show the comparison.

benchopt_cli(f"run {benchmark.benchmark_dir} -n 20 -r 4")

# %%
# Here, you see that the Julia solver is faster than the Python one.
# You also notice that the first iteration seems to take much longer than the
# other, hinting to a loading time for the solver.

# sphinx_gallery_thumbnail_number = -1
# sphinx_gallery_start_ignore
# Generate thumbnail for the sphinx gallery
benchopt_cli(
    f"plot {benchmark.benchmark_dir} --no-html --kind objective_curve"
)
# sphinx_gallery_end_ignore
