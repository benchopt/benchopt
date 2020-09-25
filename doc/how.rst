.. _how:

Write a benchmark
=================

.. contents:: Contents
   :local:
   :depth: 2

A benchmark is defined in a folder that should respect a certain
structure. Examples of benchmarks are available in the
`benchmarks folder <https://github.com/benchopt/benchOpt/tree/master/benchmarks>`_
of the `benchOpt repository <https://github.com/benchopt/benchOpt>`_
or in repository of the `benchopt organisation <https://github.com/benchopt/>`_.
The simplest way to create a benchmark is to copy an existing folder and
modify the element to fit the new structure.

A benchmark consists in three elements: an objective function,
a list of datasets, and a list of solvers.


1. Objective
------------

The objective function is defined through a Python class that
allows to evaluate the function that should be minimized by solvers.
A objective should define a `set_data` method that allows
to specify the data and a `compute` method that allows
to evaluate the objective for a given value of the iterate.

Example
~~~~~~~

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/objective.py

2. Datasets
-----------

A dataset defines what can be passed to the `set_data` method
of an objective. A dataset should implement a `get_data` method
whose output can be passed to the `set_data` of an objective.

Example
~~~~~~~

Using a real dataset:

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/datasets/boston.py

You can also define a parametrized dataset for example to test
across problem dimensions.

Example of parametrized dataset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using simulated data:

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/datasets/simulated.py

3. Solvers
----------

Solver requires to define a `set_objective` that is constructed
from the union of the data and the objective parameters.

You can define your custom solver.

Example of hand written and parametrized solver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using a hand written solver:

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/solvers/python_pgd.py

Example of a solver available from a package on conda
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using a package available from conda:

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/solvers/sklearn.py

Example of a solver available from a package available from source
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using a package available from source:

.. literalinclude:: ../benchopt/tests/test_benchmarks/dummy_benchmark/solvers/celer.py

