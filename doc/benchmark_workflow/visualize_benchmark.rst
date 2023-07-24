.. _visualize_benchmark:

Visualize a benchmark
=====================

After running a benchmark, benchopt build automatically a dashboard
to display the output of the benchmark. The dashboard is in ``HTML`` format
so that it can be easily shared.

Let's explore the dashboard features on Benchmark Lasso.

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

Part 3: Legend
--------------

The legend maps every curve to a solver. Click a legend item to hide/show its corresponding solver
Similarly, Double-click a legend item to hide/show all the rest of solvers.
Also, hovering over a legend item shows a tooltip with details about the solver.

Part 4: Sidebar
---------------

The first two dropdown menus, **Data** and **Objective**, enables to select a benchmark setup.
**Data** dropdown contains all the datasets included in the benchmarks as well as their parameters.
The same as for **Objective**.

**Objective_column** exposes all the tracked metrics along the benchmark run.

**Chart_type** apply transformations on the metric to display for instance suboptimality ``metric - min(metric)``.

**Scale** enables to decide on putting linear or log scale on the x and y axis of the figure.

**X-axis** is change the quantity plotted in the x-axis. Hence plotting the metric as a function of time, iteration, or tolerance.

**Quantiles** is a toggler to show/hide quantile in case of running the benchmark with several repetitions. 
