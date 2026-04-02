"""Configure plot views in a benchmark
===================================

This example shows how to configure plots in a benchmark, with ``config.yml``,
and custom plots.
"""

from benchopt.helpers.run_examples import ExampleBenchmark
from benchopt.helpers.run_examples import benchopt_cli

# %%
# Start with a minimal benchmark, with one objective, one dataset and
# one solver. This benchmark has no ``config.yml`` file specifying plotting
# options.

benchmark = ExampleBenchmark(
    base="minimal_benchmark", name="minimal_benchmark",
    ignore=["custom_plot.py", "example_config.yml"]
)
benchmark

# %%
# Run the benchmark to generate results.

benchopt_cli(f"run {benchmark.benchmark_dir} -n 20 -r 2")

# %%
# Define two simple saved views in ``config.yml``. The first one is a log-log
# plot, showing the objective curve, while the second one is a bar chart
# showing the runtime of each solver.
#
# In practice, you can create these interactively from the HTML result using
# the ``Save as view`` button once you have a view that is representative of
# your benchmark, then hit the ``Configs`` button in the Download area and
# save the file as a new ``config.yml`` in your benchmark.

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
# Re-generate the HTML report from the latest results using ``benchopt plot``.
# The resulting HTML page now loads the first of the two views automatically,
# and the two views are available as options in the to of the page.

benchopt_cli(f"plot {benchmark.benchmark_dir}")

# %%
# In some cases, the default plots are not suitable to visualize the results.
# With ``benchopt``, it is possible to define custom plots that integrate
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
        scale: linear
      Subopt. (log):
        plot_kind: objective_curve
        scale: loglog
      Runtimes:
        plot_kind: bar_chart
    '''
})

benchopt_cli(f"plot {benchmark.benchmark_dir}")
