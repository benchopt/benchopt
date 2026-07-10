"""Configure views in a benchmark's visuzalization
===============================================

This example shows how to configure views in a benchmark visualization
with ``config.yml`` and how to add custom plots to your benchmark.
"""

# Import example helpers to define benchmarks and run benchopt in this example
# sphinx_gallery_thumbnail_number = -1
from benchopt.helpers.run_examples import ExampleBenchmark
from benchopt.helpers.run_examples import benchopt_cli

# %%
# Start with a minimal benchmark, including an objective, one dataset and
# one solver. This benchmark has no ``config.yml`` file specifying plotting
# options.

benchmark = ExampleBenchmark(
    base="minimal_benchmark", name="minimal_benchmark",
    ignore=["custom_plot.py", "example_config.yml", "config.yml"]
)
benchmark

# %%
# Run the benchmark to generate results. This will display a first HTML page
# based on benchopt's default plotting configuration.

benchopt_cli(
    f"run {benchmark.benchmark_dir} -n 40 -r 2 -s gd[lr=[1e-1,3e-2,1e-2,3e-3]]"
)

# %%
# The default plots are generated from the results, showing the evolution of
# the first key of the objective against time. Options in the ``Change plot>``
# menu or the side bar allow to change this plot, changing the objective key,
# the x-axis or scale, or the type of plot. However, these options are reset
# when reloading the page. The concept of ``views`` allows to save specific
# configurations of the plot, that can be easily loaded.
#
# In practice, you can create these interactively from the HTML result using
# the ``Save as view`` button once you have a view that is representative of
# your benchmark, then hit the ``Configs`` button in the Download area and
# save the file as a new ``config.yml`` in your benchmark. You can also
# directly write the ``config.yml`` file, as shown below.
#
# Here, we define two simple views in ``config.yml``. The first one is a
# log-log evolution plot, showing the objective curve as a function of time,
# while the second one is a bar chart showing the runtime of each solver.
# When defining a view, part of the plotting parameters can be left free.
# They will be kept as they are when activating the view.

benchmark.update(extra_files={
    "config.yml": '''
    plot_configs:
      Subopt. (log):
        plot_kind: objective_curve
        scale: loglog
      Runtimes:
        plot_kind: bar_chart
    '''
})

# %%
# To re-generate the HTML report from the latest results, call
# ``benchopt plot``. This will override the existing HTML page, which now has
# two views available in ``Available plot view`` at the top of the page, and
# the first view automatically loaded.

benchopt_cli(f"plot {benchmark.benchmark_dir}")

# %%
# In some cases, the default plots are not suitable to visualize the results.
# With ``benchopt``. It is possible to define custom plots that integrate
# seamlessly with the HTML interface. Here, we define a custom plot that shows
# the final objective value achieved by each solver against the runtime,
# with colors defined by the value of the learning rate used by the solver.

benchmark.update(plots={
    "custom_objective_time.py": '''
    from benchopt import BasePlot


    class Plot(BasePlot):
        name = "custom_objective_time"
        type = "scatter"
        options = {}

        def plot(self, df):
            points = []
            for solver in df['solver_name'].unique():
                sub_df = df.query("solver_name == @solver").sort_values('time')
                points.append({
                    "x": sub_df["p_solver_lr"].iloc[-1:].tolist(),
                    "y": sub_df["objective_value"].iloc[-1:].tolist(),
                    "label": solver,
                    **self.get_style(solver),
                })
            return points

        def get_metadata(self, df):
            return {
                "title": "Objective against learning rate",
                "xlabel": "learning rate",
                "ylabel": "objective value",
            }
    '''
})

# %%
# This custom plot is rendered using a scatter plot, as disclosed in ``type``.
# The ``get_metadata`` method defines global options for the plot, like the
# title and the axis labels, while the ``plot`` method defines the data to be
# plotted. For a scatter plot, this corresponds to a list of points or curves,
# with their x and y coordinates, labels and colors.
# The ``options`` attribute is empty here, but it can be used to define
# user-configurable options for the plot, that will be displayed in the HTML.
# More details on the plot API can be found in :ref:`add_custom_plot`.
#
# We can then update ``plot_configs`` to include one view for the new custom
# plot, and run ``benchopt plot`` again to update the plot.

benchmark.update(extra_files={
    "config.yml": '''
    plot_configs:
      Sensitivity lr:
        plot_kind: custom_objective_time
        scale: loglog
      Subopt. (log):
        plot_kind: objective_curve
        scale: loglog
      Runtimes:
        plot_kind: bar_chart
    '''
})

# %%
# Now running `benchopt plot` again will update the HTML page with the new plot
# option and the new view, showing the sensitivity of the final objective value
# to the selection of the learning rate.

benchopt_cli(f"plot {benchmark.benchmark_dir}")

# %%
# Note that you can also generate custom plot as pdf using the ``--no-html``
# option:

benchopt_cli(
    f"plot {benchmark.benchmark_dir} -k custom_objective_time --no-html"
)
