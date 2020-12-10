.. _how:

Write a benchmark
=================

A benchmark consists in three elements: an objective_ function,
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
This class allows to evaluate the objective function to be minimized
by the solvers. An objective class should define 3 methods:

  - **set_data**: it allows to specify the data. See the data as a dictionary
    of Python variables without any constraint.
  - **compute**: it allows to evaluate the objective for a given value
    of the iterate. This method should take only one parameter.
  - **to_dict**: method that returns a dictionary to be passed
    to the **set_objective** methods of solvers_.

An objective class also needs to inherit from a base class called `BaseObjective`.

Example
~~~~~~~

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/objective.py

.. _datasets:

2. Datasets
-----------

A dataset defines what can be passed to an objective. More specifically,
a dataset should implement one method:

   - **get_data**: A method whose output consists of two things. First it outputs
     the dimension of the optization problem (size of the iterates). Second it
     outputs a dictionary that can be passed as `**kwargs` to
     the **set_data** method of an objective_.

A dataset class also needs to inherit from a base class called `BaseDataset`.

Example using a real dataset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/datasets/boston.py

You can also define a parametrized simulated dataset for example to test
across problem dimensions.

Example of parametrized simulated dataset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes one wants to test the solvers for variants of the same dataset.
For example, one may want to change the dataset size, the noise level etc.
To be able to specify parameters to get a dataset you can use a class
attribute called `parameters`. This parameter must be a dictionary
whose keys can be passed to the `__init__` of the class. The benchopt
will automatically allow you to test all combinations of parameters.

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/datasets/simulated.py

.. _solvers:

3. Solvers
----------

Solver requires to define three methods:

   - **set_objective**: This method expects as input the union of what is returned
     by the **get_data** methods of both the dataset and the objective.

   - **run**: This method takes only one parameter that controls the stopping
     condition of the solver. This is typically a number of iterations
     or a tolerance parameter.

   - **get_result**: This method returns a variable that can be passed
     to the **compute** method from the objective. This is the value of
     the iterates.

benchopt supports different types of solvers:

   - :ref:`python_numpy_solvers`
   - :ref:`python_conda_solvers`
   - :ref:`python_source_solvers`
   - :ref:`r_solvers`
   - :ref:`julia_solvers`

.. _python_numpy_solvers:

Python solver based on Numpy, Scipy, Numba
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Such solvers are written in pure `Python <https://www.python.org/>`_ without any compiled
code. They are typically written in `Numpy <https://numpy.org/>`_ and possibly
with some just in time compilation e.g. with `Numba <https://numba.pydata.org/>`_.

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/solvers/python_pgd.py

.. _python_conda_solvers:

Python solver from Conda package
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to compare a solver available on conda you can specify
how this solver needs to be installed and how to call it.
The `install_cmd` class variable needs to be set to `conda`
and the list of conda packages is specified in the variable
`requirements` that needs to be a list. See example:

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/solvers/sklearn.py

.. _python_source_solvers:

Python solver from source distrution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::
    A package available from source may require a C++
    or Fortran compiler.

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/solvers/celer.py

.. _r_solvers:

R solver
~~~~~~~~

.. _julia_solvers:

Julia solver
~~~~~~~~~~~~
