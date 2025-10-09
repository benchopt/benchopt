"""Running an existing benchmark
=============================

This Example demonstrates how to run an existing benchmark with benchopt.
It uses the `benchopt_run` helper function to run the benchmark, which runs
programatically the equivalent of the command line interface:
"""

from benchopt.helpers.run_examples import benchopt_run

# %%
# To run the benchmark, just execute:
#

benchopt_run('minimal_benchmark', n=20, r=2)

# %%
# This runs the benchmark named ``minimal_benchmark``` located in the
# ``examples`` folder.
#
# The parameters ``n``  controls the number of point on the curves, while ``r``
# controls the number of repetitions for each solver. The repetitions are used
# to compute the median and quartiles of the curves.
#
# To get a more precise curve, you can increase ``n`` and ``r``:

benchopt_run('minimal_benchmark', n=30, r=5)
