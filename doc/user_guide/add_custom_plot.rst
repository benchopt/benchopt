
.. _add_custom_plot:

Add a custom plot to a benchmark
================================

Benchopt provides a set of default plots to visualize the results of a benchmark.
These plots can be complemented with custom plots, defined in the benchmark,
to visualize the results in a different way. These plots are defined in the
:code:`plots` directory, by adding python files with classes inheriting from
:class:`benchopt.BasePlot`. This page details the API to generate custom
visualizations for your benchmark.

Structure of a custom plot
--------------------------

A custom plot is defined by a class inheriting from :class:`benchopt.BasePlot` and implementing:

- :code:`name`: The name of the plot title. This will be the name that appears
  in the plot selection menu of the HTML interface, or the name you can use to
  select this plot in config files for your benchmark.
- :code:`type`: The type of the plot, which defines how the output of `plot`
  will be rendered. Supported types are :code:`"scatter"`, :code:`"bar_chart"`,
  :code:`"boxplot"` and :code:`"table"`.
- :code:`options`: A dictionary defining the different options available for the
  plot. Typically, this can be used to have different plots depending on dataset's
  or objective's parameters, or to display customization options. The keys in the
  dictionary are the names of the options, associated to a list of their possible
  values. If a key :code:`objective/dataset/solver/objective_column` is associated
  with the value :code:`...`, the options are automatically inferred from the
  results DataFrame, as all unique values associated with this key.
- :code:`plot(self, df, **kwargs)`: give the data to produce one plot, that is
  rendered with the plotly or matplotlib backend. The method takes the results DataFrame
  and the options values as arguments, and returns the plot data. The output
  depends on the plot's type, and are detailed below for each of them.
- :code:`get_metadata(self, df, **kwargs)`: Gives global information about the plot, such
  as the title and axis labels. The method takes the results DataFrame and the options
  values as arguments, and returns the metadata of the plot, which is specific to each
  plot type.

The :code:`get_metadata` method allow to change global properties of
the resulting visualization, and the :code:`plot` method outputs the data
necessary to render it.
The visualization is rendered using either the ``plotly`` or ``matplotly`` backend.

.. code-block:: python

    from benchopt import BasePlot

    class Plot(BasePlot):
        name = "My Custom Plot"
        type = "scatter"  # or "bar_chart", "boxplot" or "table"
        options = {
            "dataset": ...,         # Automatic options from DataFrame columns
            "objective": ...,
            "my_parameter": [1, 2], # custom options
        }

        # The inputs args of this method correspond to `df` and
        # the keys in the `options` dictionary.
        def plot(self, df, dataset, objective, my_parameter):
            # ... process df ...
            return plot_data

        def get_metadata(self, df, dataset, objective, my_parameter):
            return {
                "title": f"Plot for {dataset}",
                "xlabel": "X Label",
                "ylabel": "Y Label",
            }


Plot Options
------------

The :code:`options` dictionary keys define the arguments passed to
:code:`plot` and :code:`get_metadata`. Special keys like
:code:`dataset`, :code:`objective`, :code:`solver` will automatically
try to match columns in the dataframe. Using :code:`...` as a value
will populate the options with all unique values from the dataframe
column :code:`{key}_name` (e.g. :code:`dataset_name`).


Scatter Plot
------------

For a scatter plot, the :code:`plot` method should return a list of dictionaries, where
each dictionary represents a trace in the plot. Each dictionary must contain:

- :code:`x`: A list of x values.
- :code:`y`: A list of y values.
- :code:`label`: The label of the trace

Optional keys:

- :code:`color`: The color of the trace.
- :code:`marker`: The marker style of the trace.
- :code:`x_low`, :code:`x_high`: Lists of values to display uncertainty in the plot.
  They will be used to display shaded area around the plot.

The metadata dictionary returned by :code:`get_metadata` should contain:

- :code:`title`: The title of the plot.
- :code:`xlabel`: The label of the x-axis.
- :code:`ylabel`: The label of the y-axis.

.. code-block:: python

    def plot(self, df, dataset, objective, my_parameter):
        # Filter the dataframe
        df = df.query(
            "dataset_name == @dataset and objective_name == @objective"
        )

        plot_traces = []
        for solver, df_solver in df.groupby('solver_name'):
            # Compute the median over the repetitions
            curve = (
                df_solver.groupby("stop_val")[["time", "'objective_value"]]
                .median()
            )
            plot_traces.append({
                "x": curve['time'].tolist(),
                "y": curve['objective_value'].tolist(),
                "label": solver,
                **self.get_style(solver)
            })
        return plot_traces

    def get_metadata(self, df, dataset, objective, my_parameter):
        return {
            "title": f"Convergence for {dataset}",
            "xlabel": "Time [sec]",
            "ylabel": "Objective value",
        }

.. note::
   To help with consistent style accross figures, you can use
   the helper ``get_style``, as described in :ref:`plotting_utilities`.


Bar Chart
---------

For a bar chart, the :code:`plot` method should return a list of dictionaries,
where each dictionary represents a bar. For each bar, the median value will be
used to determine its height, while the individual values will be displayed as
scatter points. The dictionary should contain:

- :code:`y`: The list of values for the bar (the median will be the height of the bar).
- :code:`label`: The label of the bar.

Optional keys:

- :code:`color`: The color of the bar.
- :code:`text`: The text to display on the bar.

The metadata dictionary returned by :code:`get_metadata` should contain:

- :code:`title`: The title of the plot.
- :code:`ylabel`: The label of the y-axis.

.. code-block:: python

    def plot(self, df, dataset, objective, **kwargs):
        df = df.query(
            "dataset_name == @dataset and objective_name == @objective"
        )
        bars = []
        for solver, df_solver in df.groupby('solver_name'):
            # Select the total runtime for each repetition
            runtimes = df_solver.groupby("idx_rep")["runtime"].last()
            bars.append({
                "y": runtimes.tolist(),
                "label": solver,
                "text": "",
                "color": self.get_style(solver)['color']
            })
        return bars

    def get_metadata(self, df, dataset, objective, **kwargs):
        return {
            "title": f"Average times for {objective} on {dataset}",
            "ylabel": "Time [sec]",
        }


Box Plot
--------

For a box plot, the :code:`plot` method should return a list of dictionaries,
where each dictionary represents a box. Each dictionary should contain:

- :code:`x`: The x coordinate.
- :code:`y`: The values of the box for the corresponding x coordinate.
- :code:`label`: The label of the box.

Optional keys:

- :code:`color`: The color of the box.

The metadata dictionary returned by :code:`get_metadata` should contain:

- :code:`title`: The title of the plot.
- :code:`xlabel`: The label of the x-axis.
- :code:`ylabel`: The label of the y-axis.

.. code-block:: python

    def plot(self, df, dataset, objective, **kwargs):
        df = df.query(
            "dataset_name == @dataset and objective_name == @objective"
        )
        plot_data = []
        for solver, df_solver in df.groupby('solver_name'):
            # Example: boxplot for the final objective values
            # for each solver
            final_objective_value = (
                df_solver.groupby("idx_rep")['objective_value'].last()
            )
            plot_data.append({
                "x": [solver],
                "y": [final_objective_value.tolist()],
                "label": solver,
                "color": self.get_style(solver)['color']
            })
        return plot_data

    def get_metadata(self, df, dataset, objective, **kwargs):
        return {
            "title": f"Boxplot for {objective} on {dataset}",
            "xlabel": "Solver",
            "ylabel": "Objective value",
        }


Table Plot
----------

For a table plot, the :code:`plot` method should return a list of lists,
where each inner list represents a row in the table.
The metadata dictionary returned by :code:`get_metadata` should contain:

- :code:`title`: The title of the plot.
- :code:`columns`: A list of column names.

.. code-block:: python

    def plot(self, df, dataset, objective, **kwargs):
        df = df.query(
            "dataset_name == @dataset and objective_name == @objective"
        )
        rows = []
        for solver, df_solver in df.groupby('solver_name'):
            # Example: table with solver name and mean time
            # when using `sampling_strategy = 'run_once'`
            rows.append([solver, df_solver['time'].mean()])
        return rows

    def get_metadata(self, df, dataset, objective, **kwargs):
        return {
            "title": f"Summary for {dataset}",
            "columns": ["Solver", "Mean Time [sec]"],
        }


.. _plotting_utilities:
Plotting Utilities
------------------

To ensure consistency across plots (e.g., using the same color and marker for a
given solver), :class:`benchopt.BasePlot` provides the helper method
:code:`get_style(label)`. This method returns a dictionary with :code:`color`
and :code:`marker` keys, which can be directly unpacked into the trace dictionary
for scatter plots or used to select the color for other plot types. It
automatically assigns a color from the default color palette based on the hash
of the label, ensuring that the same solver always gets the same color.

.. code-block:: python

    # Usage in plot()
    style = self.get_style(solver_name)
    trace = {
        # ...
        "color": style["color"],
        "marker": style["marker"]
    }
    # Or simply:
    trace = {
        # ...
        **self.get_style(solver_name)
    }

