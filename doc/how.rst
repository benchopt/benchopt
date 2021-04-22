.. _how:

Write a benchmark
=================

A benchmark is composed of three elements: an objective_ function,
a list of datasets_, and a list of solvers_.

A benchmark is defined in a folder that should respect a certain
structure. For example::

    my_benchmark/
    ├── README.rst
    ├── datasets
    │   ├── simulated.py  # some dataset
    │   └── real.py  # some dataset
    ├── objective.py  # contains the definition of the objective
    └── solvers
        ├── solver1.py  # some solver
        └── solver2.py  # some solver

Examples of actual benchmarks are available in the
`benchOpt organisation <https://github.com/benchopt/>`_ such
as for `Ordinary Least Square (OLS) <https://github.com/benchopt/benchmark_ols>`_,
`Lasso <https://github.com/benchopt/benchmark_lasso>`_ or
`L1-regularized logistic regression <https://github.com/benchopt/benchmark_logreg_l1>`_.

.. note::

    The simplest way to create a benchmark is to copy an existing folder and
    modify the element to fit the new structure.


.. _objective:

1. Objective
------------

The **objective function** is defined through a Python class.
This class allows to monitor the quantities of interest along the iterations
of the solvers. Typically it allows to evaluate the objective function to
be minimized by the solvers. An objective class should define 3 methods:

  - ``set_data(**data)``: it allows to specify the data. See the data as a dictionary
    of Python variables without any constraint.
  - ``compute(x)``: it allows to evaluate the objective for a given value
    of the iterate, here called ``x``. This method should take only one parameter,
    the output returned by the solver. All other parameters should be stored
    in the class with ``set_data`` method.
  - ``to_dict()``: method that returns a dictionary to be passed
    to the ``set_objective`` methods of solvers_.

An objective class also needs to inherit from a base class called
:class:`benchopt.base.BaseObjective`.

Multiple values can be computed in one objective as long as they are
stored in a dictionary with a key being `objective_value`. This allows
to compute different metrics at once.

Example
~~~~~~~

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/doc_objective.py

.. _datasets:

2. Datasets
-----------

A dataset defines what can be passed to an objective. More specifically,
a dataset should implement one method:

   - ``get_data()``: A method whose output consists of two things. First it outputs
     the dimension of the optimization problem (size of the iterates). Second it
     outputs a dictionary that can be passed as keyword arguments ``**data`` to
     the ``set_data`` method of an objective_.

A dataset class also needs to inherit from a base class called
:class:`benchopt.BaseDataset`.

Example using a real dataset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/datasets/boston.py

You can also define a parametrized simulated dataset for example to test
across problem dimensions.

Example of parametrized simulated dataset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes one wants to test the solvers for variants of the same dataset.
For example, one may want to change the dataset size, the noise level, etc.
To be able to specify parameters to get a dataset, you can use a class
attribute called ``parameters``. This parameter must be a dictionary
whose keys can be passed to the ``__init__`` of the class. Then BenchOpt
will automatically allow you to test all combinations of parameters.

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/datasets/simulated.py

.. _solvers:

3. Solvers
----------

A solver requires to define three methods:

   - ``set_objective(**objective_dict)``: This method will be called with the
     dictionary ``objective_dict`` returned by the method ``to_dict``
     from the objective. The goal of this method is to provide all necessary
     information to the solver so it can optimize the objective function.

   - ``run(stop_value)``: This method takes only one parameter that controls the stopping
     condition of the solver. This is typically a number of iterations ``n_iter``
     or a tolerance parameter ``tol``. Alternatively, a ``callback`` function that will be
     called at each iteration can be passed. The callback returns ``False`` once the
     computation should stop. The parameter is controlled by the ``stop_strategy``,
     see below for details.

   - ``get_result()``: This method returns a variable that can be passed
     to the ``compute`` method from the objective. This is the output of
     the solver.

**Stop strategy:**

A solver should also define a ``stop_strategy`` as class attribute.
This ``stop_strategy`` can be:

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

BenchOpt supports different types of solvers:

   - :ref:`python_solvers`
   - :ref:`r_solvers`
   - :ref:`julia_solvers`
   - :ref:`source_solvers`

.. _python_solvers:

Python solver
~~~~~~~~~~~~~

The simplest solvers to use are solvers written in pure
`Python <https://www.python.org/>`_ without any compiled
code. They are typically written in `Numpy <https://numpy.org/>`_
with no other dependencies. Here is an example:

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/solvers/python_pgd.py

For solvers that allow access to each iterate of the solution, using ``"callback"``
as a ``stop_strategy`` implies a slight modification for ``run``. A ``callback`` should be called at
each iteration with parameter the current value of the iterate.
Here is an example in the same situation as above:

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/solvers/python_pgd_callback.py
  :pyobject: Solver.run

If your Python solver requires some packages such as `Numba <https://numba.pydata.org/>`_,
BenchOpt allows you to list some requirements. The necessary packages should be available
via `conda <https://docs.conda.io/en/latest/>`_ or
`pip <https://packaging.python.org/guides/tool-recommendations/>`_.

In this case the ``install_cmd`` class variable needs to be set to ``'conda'``
and the list of needed packages is specified in the variable
``requirements`` that needs to be a Python list. If a requirement
starts with ``pip:`` then the package is installed from `pypi <https://pypi.org/>`_ and
not `conda-forge <https://conda-forge.org/>`_. See example:

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/solvers/sklearn.py

.. note::

    The ``install_cmd`` can either be ``'conda'`` or ``'shell'``. If ``'shell'``
    a shell script is necessary to explain how to setup the required
    dependencies. See :ref:`source_solvers`.

.. note::

    Specifying the dependencies is necessary if you let BenchOpt
    manage the creation of a dedicated environment. If you want to
    use your local environment the list of dependencies is
    not relevant. See :ref:`cli_documentation`.

.. _r_solvers:

R solver
~~~~~~~~

A solver written in `R <https://www.r-project.org/>`_ needs two files.
A ``.R`` file that contains the solver and a ``.py`` file that knows how to call the
R solver using `Rpy2 <https://pypi.org/project/rpy2/>`_. Only the extensions
should differ between the two files. Here is the Python file:

.. literalinclude:: ../benchmarks/lasso/solvers/r_pgd.py

It uses the R code in:

.. literalinclude:: ../benchmarks/lasso/solvers/r_pgd.R
    :language: R

.. note::

    This uses the function :func:`benchopt.safe_import_context` to avoid
    a crash when R is not available. The solver is in this case
    just skipped.

.. _julia_solvers:

Julia solver
~~~~~~~~~~~~

A solver written in `Julia <https://julialang.org>`_ needs two files.
A ``.jl`` file that contains the solver and a ``.py`` file that knows how to call the
Julia solver using `PyJulia <https://pypi.org/project/julia/>`_. Only the extensions
should differ between the two files. Here is the Python file:

.. literalinclude:: ../benchmarks/lasso/solvers/julia_pgd.py

It uses the Julia code in:

.. literalinclude:: ../benchmarks/lasso/solvers/julia_pgd.jl
    :language: julia

.. _source_solvers:

Solver from source
~~~~~~~~~~~~~~~~~~

You can install a package from source in case it is not available
as binaries from the package managers from either Python, R or Julia.

.. note::
    A package available from source may require a C++
    or Fortran compiler.

Here is example using pip from a Python package on GitHub:

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/solvers/celer.py

.. note::

    See for example on the L1 logistic regression benchmark for
    `an example <https://github.com/benchopt/benchmark_logreg_l1/blob/master/solvers/liblinear.py>`_
    that uses a ``'shell'`` as ``install_cmd``.
