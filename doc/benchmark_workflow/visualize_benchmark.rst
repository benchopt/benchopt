.. _visualize_benchmark:

Visualize a benchmark
=====================

After running a benchmark, benchopt build automatically a dashboard
to display the output of the benchmark. The dashboard is in ``HTML`` format
so that it can be easily shared.

Let's explore the dashboard features on Benchmark Lasso.

.. Hint::

    Head to :ref:`get_started` to learn how to install benchopt
    and setup the Benchmark Lasso accordingly.

.. figure:: ../_static/annotated_benchmark_dashboard.png
   :align: center
   :alt: Dashboard of the Lasso benchmark results


Part 1: Header
--------------

Here are the metadata of the benchmark namely the title of the benchmark
and the specifications of the machine used to run it. On the right hand side,
there is a button :kbd:`Download` to download the output of the benchmark as ``.parquet`` file.

Part 2: Figure
--------------

Here is the main figure that plots the tracked metrics throughout the benchmark run.
Its title shows the objective and the dataset names and their corresponding parameters
that produced the plot.

Hover over the figure will make a modebar appears in the right side.
This can be used to interact with the figure, e.g. zoom in and out on particular regions.

Part 3: Legend
--------------

The legend maps every curve to a solver.

Click a legend item to hide/show its corresponding solver Similarly, Double-click a legend item
to hide/show all the rest of solvers. Also, hovering over a legend item shows a tooltip with details about the solver.

.. note::

    Details about the solver can be included by adding docstring to the solver.

Part 4: Sidebar
---------------

The first two dropdown menus, **Data** and **Objective**, enables to select a benchmark setup.
The **Data** dropdown contains all the datasets included in the benchmarks as well as their parameters.
the same as for **Objective** dropdown.

The **Objective_column** exposes all the tracked metrics along the benchmark run.
Those metrics were defined in the ``Objective`` and corresponds to the quantities returned by ``evaluate_result``.

Hover over the question mark to show a tooltip with details about the objective.

.. note::

    Details about the Objective can be included by adding docstring to the Objective.

On the other hand, **Chart_type** apply transformations on the metric to display for instance suboptimality ``metric - min(metric)`` and
relative suboptimality ``metric - min(metric) / metric[0] - min(metric)``.

Use **Scale** to set ``x`` and ``y`` axis scale to linear or logarithmic.

Similarly, use **X-axis** to change the quantity plotted in the x-axis and therefore plotting the metric as a function of *Time*, *Iteration*, or *Tolerance*.

Finally, **Quantiles** is a toggler to show/hide ``95th - 5th`` quantiles in case of running the benchmark with several repetitions. 
