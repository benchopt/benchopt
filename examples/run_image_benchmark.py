"""Image plot type for benchopt
==============================

This example demonstrates the ``image`` plot type, which allows
benchmark authors to display solver outputs (or any generated
image) as a visual gallery inside the benchopt HTML result page.

The benchmark solves a toy 2-D signal denoising problem. Each
solver stores its intermediate iterates, and the custom
``ReconstructionImagePlot`` plot class encodes the final
reconstruction of every solver as a PNG image embedded in the HTML
page.
"""

from benchopt.helpers.run_examples import ExampleBenchmark
from benchopt.helpers.run_examples import benchopt_cli

# %%
# The benchmark is defined in ``examples/image_benchmark``.
# It contains:
#
# - an ``Objective`` that measures MSE on a noisy 2-D checkerboard;
# - a ``Dataset`` (``simulated``) that generates the noisy signal;
# - two solvers (``gaussian_filter`` and ``tv_denoise``) that denoise
#   the signal iteratively and store every iterate;
# - a custom ``plots/reconstruction.py`` that implements a
#   ``BasePlot`` subclass with ``type = "image"``.

benchmark = ExampleBenchmark(base="image_benchmark", name="image_benchmark")
benchmark

# %%
# Run the benchmark with a small number of iterations and repetitions
# to keep the runtime short.

benchopt_cli(
    f"run {benchmark.benchmark_dir} -n 5 -r 1 --no-plot"
)

# %%
# The resulting HTML page contains a new "reconstruction" chart type
# in the *Chart type* dropdown. Selecting it renders a responsive
# image grid showing the final denoised image produced by each solver.
#
# The image data is embedded as base64-encoded PNGs directly in the
# HTML file, so the page is fully self-contained and can be shared
# without any external assets.
