"""Running an existing benchmark
=============================

This example demonstrates how to run an existing benchmark with benchopt.
"""

# Import example helpers to define the benchmark and
# programmatically call the CLI.
# sphinx_gallery_thumbnail_number = -1
from benchopt.helpers.run_examples import ExampleBenchmark
from benchopt.helpers.run_examples import benchopt_cli

# %%
# We will use the minimal benchmark defined in the ``examples`` folder.
# The benchmark objective is a simple minimization task:
#
# .. math::
#
#     \min_{\hat{X}} \; \mathrm{MSE}(X, \hat{X})
#
# We define:
#
# - an ``Objective`` that evaluates MSE between ``X`` and ``X_hat``;
# - a ``Dataset`` that generates a random matrix ``X``;
# - a ``Solver`` that minimizes this objective with gradient descent. It is
#   parametrized with parameter ``lr`` for the step size.

benchmark = ExampleBenchmark(
    base="minimal_benchmark", name="minimal_benchmark",
    ignore=["custom_plot.py", "example_config.yml"]
)
benchmark

# %%
# To run the benchmark, just execute:
#

benchopt_cli(f"run {benchmark.benchmark_dir} -n 20 -r 2")

# %%
# This runs the benchmark named ``minimal_benchmark`` located in the
# ``examples`` folder.
#
# The parameters ``n``  controls the number of point on the curves, while ``r``
# controls the number of repetitions for each solver. The repetitions are used
# to compute the median and quartiles of the curves.
#
# To get a more precise curve, you can increase ``n`` and ``r``:

benchopt_cli(f"run {benchmark.benchmark_dir} -n 30 -r 5")

# %%
# Here, the display is not ideal because both solvers reach convergence very
# quickly. You can change the display by selecting the scale of the axis in
# the plot configuration panel.
# Go to the *Change plot* banner at the top of the HTML file, and change the
# scale to ``loglog`` on the drop down menu.
#
# Note that for convenience, this can be saved as a view in the configuration
# of the benchmark. See :ref:`here <plot_configs>` for more details.
# Here, clicking on ``Subopt. (log)`` in the *Available plots* above the
# figure will take you to a view with the right scale, and looking at
# suboptimality instead of objective value.
#
# Once the benchmark has be run, you can also generate pdf figures using the
# ``benchopt plot`` command with ``--no-html`` option:

benchopt_cli(
    f"plot {benchmark.benchmark_dir} -k objective_curve --no-html"
)

# %%
# See :ref:`here <add_custom_plot>` for more details on how to customize
# the plots and define your own visualization.
