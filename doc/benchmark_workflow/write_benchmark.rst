.. _write_benchmark:

Write a benchmark
=================


A benchmark is composed of three elements: an objective_ function,
a list of datasets_, and a list of solvers_.

A benchmark is defined in a folder that should respect a certain
structure. For example

.. code-block::

    my_benchmark/
    ├── objective.py  # contains the definition of the objective
    ├── datasets/
    │   ├── dataset1.py  # some dataset
    │   └── dataset2.py  # some dataset
    ├── solvers/
    │   ├── solver1.py  # some solver
    │   └── solver2.py  # some solver
    └── plots/
        └── custom_plot.py  # (optional) some custom plot

Examples of actual benchmarks are available in the
`benchopt organisation <https://github.com/benchopt/>`_ such
as for `Ordinary Least Square (OLS) <https://github.com/benchopt/benchmark_ols>`_,
`Lasso <https://github.com/benchopt/benchmark_lasso>`_ or
`L1-regularized logistic regression <https://github.com/benchopt/benchmark_logreg_l1>`_.

.. note::

    The simplest way to create a benchmark is to copy an existing folder and
    to adapt its content.
    A benchmark template is provided as a `GitHub template repository here <https://github.com/benchopt/template_benchmark>`_.


.. _objective:

1. Objective
------------

The **objective function** is defined through a Python class, ``Objective``, defined in ``objective.py``.
This class allows to monitor the quantities of interest along the iterations of the solvers.
Typically it allows to evaluate the objective function to be minimized by the solvers.
An objective class should define 4 methods:

- ``set_data(**data)``: allows to specify the data. See the data as a dictionary
  of Python variables without any constraint. In the following example, the data
  contains only one variable ``X``. This data is provided by the
  ``Dataset.get_data()`` method of a dataset_.
- ``get_objective()``: returns the information that each method will need to
  provide a result. The information is also passed as a dictionary, which will
  serve as input for the ``Solver.set_objective`` method of the solvers_.
- ``evaluate_result(X_hat)``: it allows to evaluate the output of the different
  methods, here called ``X_hat``. This method should take a dictionary as
  input, which is provided by the ``Solver.get_result`` method. All other
  parameters should be stored in the class with the ``set_data`` method.
  ``evaluate_result`` should return a float (understood as the objective value)
  or a dictionary. If a dictionary is returned it should contain a key called
  ``value`` (the objective value) and all other keys should have ``float``
  values allowing to track more than one value of interest (e.g. train and test
  errors).
- ``get_one_result()``: returns one solution that can be returned by a solver.
  This defines the shape of the solution and will be used to test that the
  benchmark works properly.

An objective class needs to inherit from a base class,
:class:`benchopt.BaseObjective`.

.. note::
  Multiple metrics can be returned by ``Objective.evaluate_result`` as long as
  they are stored in a dictionary, with a key being ``value`` corresponding to the main metric to track.

Example
~~~~~~~

.. literalinclude:: ../../examples/minimal_benchmark/objective.py

.. _datasets:

2. Datasets
-----------

A dataset defines what can be passed to an objective. More specifically,
a dataset should implement one method:

- ``get_data()``: A method which outputs a dictionary that is passed as
  keyword arguments ``**data`` to the ``Objective.set_data`` method of
  the objective_.

A dataset class also needs to inherit from a base class called
:class:`benchopt.BaseDataset`.

Example
~~~~~~~

.. literalinclude:: ../../examples/minimal_benchmark/datasets/simulated.py

.. _solvers:

3. Solvers
----------

A solver must define three methods:

- ``set_objective(**objective_dict)``: Store information about the data,
  objective and initialize required quantities. This method is called with the
  dictionary returned by the method ``Objective.get_objective``.

- ``run(stop_condition)``: Run the actual method to benchmark. This is where
  the important part of the solver goes. This method takes one parameter
  controlling the stopping condition of the solver. This is either a number of
  iterations ``n_iter``, a tolerance parameter ``tol``, or a ``callback``
  function that will be called at each iteration can be passed. See the note
  bellow for more information on this parameter.

- ``get_result()``: Format the output of the method to be evaluated in the
  Objective. This method returns a dictionary that is passed to
  ``Objective.evaluate_result``.

Example
~~~~~~~

.. literalinclude:: ../../examples/minimal_benchmark/solvers/gd.py

.. note::

  **Sampling strategy:**

  A solver should also define a ``sampling_strategy`` as class attribute.
  This ``sampling_strategy`` can be:

  - ``'iteration'``: in this case the ``run`` method of the solver
    is parametrized by the number of iterations computed. The parameter
    is called ``n_iter`` and should be an integer.

  - ``'tolerance'``: in this case the ``run`` method of the solver
    is parametrized by a tolerance that should decrease with
    the running time. The parameter is called ``tol`` and should be
    a positive float.

  - ``'callback'``: in this case, the ``run`` method of the solver
    should call at each iteration the provided callback function. It will
    compute and store the objective and return ``False`` once the computations
    should stop.

  - ``'run_once'``: in this case, the ``run`` method of the solver is run only
  once during the benchmark.


.. _custom_plots:

4. Plots
--------

.. warning::

   This feature is experimental and the API may change in future releases without further notice.

Custom plots can be defined to visualize specific quantities of interest
during the benchmark. By default, BenchOpt provides some standard plots such as
the objective curve, box plots and bar plots. However, users can create their own plots
by defining a class that inherits from :class:`benchopt.BasePlot`.

A custom plot must define the following attributes:
  - ``name``: A string representing the name of the plot.
  - ``type``: A string indicating the type of plot ("scatter").
  - ``dropdown``: A dictionary specifying the dropdown options for the plot. For each dropdown
    option, provide a list of possible values, or an ellipsis (...) to indicate that the values
    should be determined dynamically based on the benchmark data, such as the list of datasets.

A custom plot must also implement 2 methods:
  - ``plot(self, df, **kwargs)``: This method takes a pandas DataFrame ``df`` as input and the keyword
    arguments from the dropdown menu and returns a list of dictionaries,
    each representing a plot trace. Each dictionary should contain the necessary information to create the plot
    (x, y, color, marker, label). Users can also use the self.get_solver_style(solver_name) method to obtain
    consistent styles for the traces.
  - ``get_metadata(self, df, **kwargs)``: This method takes a pandas DataFrame ``df`` as input and returns a dictionary
    containing metadata for the plot (title, xlabel, and ylabel).


Example
~~~~~~~

.. literalinclude:: ../../examples/minimal_benchmark/plots/custom_plot.py
