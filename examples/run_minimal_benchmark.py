"""Running an existing benchmark
=============================

This Example demonstrates how to run an existing benchmark with benchopt.
It uses the `benchopt_run` helper function to run the benchmark, which runs
programmatically the equivalent of the command line interface:
"""

from benchopt.helpers.run_examples import benchopt_run

# %%
# To run the benchmark, just execute:
#

benchopt_run('minimal_benchmark', n=20, r=2)

# %%
# This runs the benchmark named ``minimal_benchmark`` located in the
# ``examples`` folder.
#
# The parameters ``n``  controls the number of point on the curves, while ``r``
# controls the number of repetitions for each solver. The repetitions are used
# to compute the median and quartiles of the curves.
#
# To get a more precise curve, you can increase ``n`` and ``r``:

benchopt_run('minimal_benchmark', n=30, r=5)

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
