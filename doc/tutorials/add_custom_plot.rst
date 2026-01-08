
.. _add_custom_plot:

Add a custom plot to a benchmark
===============================

Benchopt provides a set of default plots to visualize the results of a benchmark.
However, it is also possible to add custom plots to a benchmark to visualize the results in a different way.
This is done by adding a :code:`plots` directory in the benchmark directory, and adding python files with classes inheriting from :class:`benchopt.BasePlot`.

Structure of a custom plot
--------------------------

A custom plot is defined as a class inheriting from :class:`benchopt.BasePlot` and implementing:

- :code:`name`: The name of the plot title.
- :code:`type`: The type of the plot. Supported types are :code:`"scatter"`, :code:`"bar_chart"`, :code:`"boxplot"` and :code:`"table"`.
- :code:`dropdown`: A dictionary defining the dropdowns available in the plot. The keys are the names of the dropdowns and the values are the options. If the value is :code:`...`, the options are automatically inferred from the results dataframe.
- :code:`plot(self, df, **kwargs)`: A method that takes the results dataframe and the dropdown values as arguments, and returns the data to plot.
- :code:`get_metadata(self, df, **kwargs)`: A method that takes the results dataframe and the dropdown values as arguments, and returns the metadata of the plot (title, labels, etc.).

.. code-block:: python

    from benchopt import BasePlot

    class Plot(BasePlot):
        name = "My Custom Plot"
        type = "scatter"  # or "bar_chart", "boxplot" or "table"
        dropdown = {
            "dataset": ...,         # Automatic options from DataFrame columns
            "objective": ...,
            "my_parameter": [1, 2], # custom options
        }

        def plot(self, df, dataset, objective, my_parameter):
            # ... process df ...
            return plot_data

        def get_metadata(self, df, dataset, objective, my_parameter):
            return {
                "title": f"Plot for {dataset}",
                "xlabel": "X Label",
                "ylabel": "Y Label",
            }

Scatter Plot
------------

For a scatter plot, the :code:`plot` method should return a list of dictionaries, where each dictionary represents a trace in the plot.
Each dictionary must contain:

- :code:`x`: A list of x values.
- :code:`y`: A list of y values.
- :code:`label`: The label of the trace

Optional keys:
- :code:`color`: The color of the trace.
- :code:`marker`: The marker style of the trace.
- :code:`q1`, :code:`q9`: Lists of values for the 10% and 90% quantiles (for shading).

.. code-block:: python

    def plot(self, df, dataset, objective, my_parameter):
        # Filter the dataframe
        df = df[df['dataset_name'] == dataset]

        traces = []
        for solver, df_solver in df.groupby('solver_name'):
            traces.append({
                "x": df_solver['time'].tolist(),
                "y": df_solver['objective_value'].tolist(),
                "label": solver,
                **self.get_style(solver)
            })
        return traces

    def get_metadata(self, df, dataset, objective, my_parameter):
        return {
            "title": f"Convergence for {dataset}",
            "xlabel": "Time [sec]",
            "ylabel": "Objective value",
        }

Bar Chart
---------

For a bar chart, the :code:`plot` method should return a list of dictionaries, where each dictionary represents a bar.
The dictionary should contain:

- :code:`y`: The list of values for the bar (the median will be the height of the bar).
- :code:`text`: The text to display on the bar.
- :code:`label`: The label of the bar.

Optional keys:

- :code:`color`: The color of the bar.

.. code-block:: python

    def plot(self, df, dataset, objective, **kwargs):
        bars = []
        for solver, df_solver in df.groupby('solver_name'):
            bars.append({
                "y": df_solver['time'].mean(),
                "times": df_solver['time'].tolist(),
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

For a box plot, the :code:`plot` method should return a list of dictionaries, where each dictionary represents a box.
Each dictionary should contain:

- :code:`x`: The x coordinate.
- :code:`y`: The values of the box for the corresponding x coordinate.
- :code:`label`: The label of the box.

Optional keys:

- :code:`color`: The color of the box.

.. code-block:: python

    def plot(self, df, dataset, objective, **kwargs):
        traces = []
        for solver, df_solver in df.groupby('solver_name'):
            # Example: boxplot of objective values for a single solver
            traces.append({
                "x": [solver],
                "y": [df_solver['objective_value'].tolist()],
                "label": solver,
                "color": self.get_style(solver)['color']
            })
        return traces

    def get_metadata(self, df, dataset, objective, **kwargs):
        return {
            "title": f"Boxplot for {objective} on {dataset}",
            "xlabel": "Solver",
            "ylabel": "Objective value",
        }

Table Plot
----------

For a table plot, the :code:`plot` method should return a list of lists, where each inner list represents a row in the table.
The :code:`get_metadata` method must return a dictionary with a :code:`columns` key, containing the list of column names.

.. code-block:: python

    def plot(self, df, dataset, objective, **kwargs):
        rows = []
        for solver, df_solver in df.groupby('solver_name'):
            # Example: table with solver name and mean time
            rows.append([solver, df_solver['time'].mean()])
        return rows

    def get_metadata(self, df, dataset, objective, **kwargs):
        return {
            "title": f"Summary for {dataset}",
            "columns": ["Solver", "Mean Time [sec]"],
        }

Metadata and Dropdowns
----------------------

The :code:`get_metadata` method is used to provide information about the plot layout. It should return a dictionary with:
- :code:`title`: The title of the plot.
- :code:`xlabel`: The label of the x-axis.
- :code:`ylabel`: The label of the y-axis.

The :code:`dropdown` dictionary keys define the arguments passed to :code:`plot` and :code:`get_metadata`.
Special keys like :code:`dataset`, :code:`objective`, :code:`solver` will automatically try to match columns in the dataframe.
Using :code:`...` as a value will populate the options with all unique values from the dataframe column :code:`{key}_name` (e.g. :code:`dataset_name`).

Plotting Utilities
------------------

To ensure consistency across plots (e.g., using the same color and marker for a given solver), :class:`benchopt.BasePlot` provides the helper method :code:`get_style(label)`.
This method returns a dictionary with :code:`color` and :code:`marker` keys, which can be directly unpacked into the trace dictionary for scatter plots or used to select the color for other plot types.
It automatically assigns a color from the default color palette based on the hash of the label, ensuring that the same solver always gets the same color.

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

