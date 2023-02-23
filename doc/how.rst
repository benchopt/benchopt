.. _how:

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
    │   ├── simulated.py  # some dataset
    │   └── real.py  # some dataset
    └── solvers/
        ├── solver1.py  # some solver
        └── solver2.py  # some solver

Examples of actual benchmarks are available in the
`benchopt organisation <https://github.com/benchopt/>`_ such
as for `Ordinary Least Square (OLS) <https://github.com/benchopt/benchmark_ols>`_,
`Lasso <https://github.com/benchopt/benchmark_lasso>`_ or
`L1-regularized logistic regression <https://github.com/benchopt/benchmark_logreg_l1>`_.

.. note::

    The simplest way to create a benchmark is to copy an existing folder and
    to adapt its content.
    A benchmark template is provided as a `GitHub template repo here <https://github.com/benchopt/template_benchmark>`_


.. _objective:

1. Objective
------------

The **objective function** is defined through a Python class.
This class allows to monitor the quantities of interest along the iterations
of the solvers. Typically it allows to evaluate the objective function to
be minimized by the solvers. An objective class should define 3 methods:

- ``get_one_solution()``: it returns one solution that can be returned by a solver.
  This defines the shape of the solution and will be used to test that the
  benchmark works properly.
- ``set_data(**data)``: it allows to specify the data. See the data as a dictionary
  of Python variables without any constraint.
- ``compute(x)``: it allows to evaluate the objective for a given value
  of the iterate, here called ``x``. This method should take only one parameter,
  the output returned by the solver. All other parameters should be stored
  in the class with the ``set_data`` method. The ``compute`` function should return
  a float (understood as the objective value) or a dictionary. If a dictionary
  is returned it should contain a key called ``value`` (the objective value) and all other keys
  should have ``float`` values allowing to track more than one value
  of interest (e.g. train and test errors).
- ``get_objective()``: method that returns a dictionary to be passed
  to the ``set_objective`` methods of solvers_.

An objective class also needs to inherit from a base class,
:class:`benchopt.BaseObjective`.

.. note::
  Multiple values can be computed in one objective as long as they are
  stored in a dictionary with a key being ``value``. This allows to compute
  different metrics at once.

Example
~~~~~~~

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/doc_objective.py

.. _datasets:

2. Datasets
-----------

A dataset defines what can be passed to an objective. More specifically,
a dataset should implement one method:

- ``get_data()``: A method which outputs a dictionary that can be passed as
  keyword arguments ``**data`` to the ``set_data`` method of an objective_.

A dataset class also needs to inherit from a base class called
:class:`benchopt.BaseDataset`.

Example using a real dataset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/datasets/leukemia.py

You can also define a parametrized simulated dataset, for example to test
across multiple problem dimensions.

Example of parametrized simulated dataset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes one wants to test the solvers for variants of the same dataset.
For example, one may want to change the dataset size, the noise level, etc.
To be able to specify parameters to get a dataset, you can use a class
attribute called ``parameters``. This parameter must be a dictionary
whose keys are passed to the ``__init__`` of the dataset class. Then Benchopt
will automatically allow you to test all combinations of parameters.

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/datasets/simulated.py

However, all of these variants will not be tested during the call to ``benchopt test``.
If you want to test different variants of the simulated dataset with ``benchopt test``,
you may use the ``test_parameters`` class attribute.
The construction of this attribute is similar to the one described above for
``parameters``. This allows you to test solvers that could not be used for a single
variant of the dataset.

.. literalinclude:: ../benchopt/tests/test_benchmarks/many_simulated_datasets/datasets/simulated.py

.. _solvers:

3. Solvers
----------

A solver must define three methods:

   - ``set_objective(**objective_dict)``: This method will be called with the
     dictionary ``objective_dict`` returned by the method ``get_objective``
     from the objective. The goal of this method is to provide all necessary
     information to the solver so it can optimize the objective function.

   - ``run(stop_value)``: This method takes only one parameter that controls the stopping
     condition of the solver. Typically this is either a number of iterations ``n_iter``
     or a tolerance parameter ``tol``. Alternatively, a ``callback`` function that will be
     called at each iteration can be passed. The callback should return ``False`` once the
     computation should stop.
     The parameter ``stop_value`` is controlled by the ``stopping_strategy``,
     see below for details.

   - ``get_result()``: This method returns a variable that can be passed
     to the ``compute`` method from the objective. This is the output of
     the solver.

**Stop strategy:**

A solver should also define a ``stopping_strategy`` as class attribute.
This ``stopping_strategy`` can be:

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

Benchopt supports different types of solvers:

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
as a ``stopping_strategy`` implies a slight modification for ``run``. A ``callback``
should be called at each iteration with parameter the current value of the iterate.
Here is an example in the same situation as above:

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/solvers/python_pgd_callback.py
  :pyobject: Solver.run

If your Python solver requires some packages such as `Numba <https://numba.pydata.org/>`_,
Benchopt allows you to list some requirements. The necessary packages should be available
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

    Specifying the dependencies is necessary if you let benchopt
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

.. literalinclude:: ../benchmarks/benchmark_lasso/solvers/r_pgd.py

It uses the R code in:

.. literalinclude:: ../benchmarks/benchmark_lasso/solvers/r_pgd.R
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

.. literalinclude:: ../benchmarks/benchmark_lasso/solvers/julia_pgd.py

It uses the Julia code in:

.. literalinclude:: ../benchmarks/benchmark_lasso/solvers/julia_pgd.jl
    :language: julia

.. admonition:: Installing Julia dependencies

  Note that it is also possible to install ``julia`` dependencies using ``benchopt install`` with the class attribute ``julia_requirements``. This attribute should be a list of package names, whose string are directly passed to ``Pkg.add``.

  In case it is necessary to install dependencies from a GitHub repository, one can use the following format: ``PkgName::https://github.com/org/Pkg.jl#branch_name``. This will be processed to recover both the url and the package name. Note that the ``branch_name`` is optional. Using the ``::`` to specify the ``PkgName`` is necessary to allow ``benchopt`` to check if it is installed in the targeted environment.

.. _source_solvers:

Solver from source
~~~~~~~~~~~~~~~~~~

You can install a package from source in case it is not available
as binaries from the package managers from either Python, R or Julia.

.. note::
    A package available from source may require a C++
    or Fortran compiler.

Here is example using pip from a Python package on GitHub:

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/solvers/sklearn.py

.. note::

    See for example on the L1 logistic regression benchmark for
    `an example <https://github.com/benchopt/benchmark_logreg_l1/blob/master/solvers/liblinear.py>`_
    that uses a ``'shell'`` as ``install_cmd``.
