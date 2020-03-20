.. _how:

Write a benchmark
=================

.. contents:: Contents
   :local:
   :depth: 2

A benchmark consists in three elements: an objective function,
a list of datasets, and a list of solvers.

A benchmark is defined in a folder that should respect a certain
structure. Examples of benchmarks are availble in the
`benchmarks folder <https://github.com/benchopt/benchOpt/tree/master/benchmarks>`_
of the `benchOpt repository <https://github.com/benchopt/benchOpt>`_

1. Objective
------------

The objective function is defined through a Python class that
allows to evaluate the function that should be minimized by solvers.
A objective should define a `set_data` method that allows
to specify the data and a `__call__` method that allows
to evaluate the objective for a given value of the iterate.

Example
~~~~~~~

.. literalinclude:: ../benchmarks/lasso/objective.py

2. Datasets
-----------

A dataset defines what can be passed to the `set_data` method
of an objective. A dataset should implement a `get_data` method
whose output can be passed to the `set_data` of an objective.

Example
~~~~~~~

Using a real dataset:

.. literalinclude:: ../benchmarks/lasso/datasets/boston.py

You can also define a parametrized dataset for example to test
across problem dimensions.

Example of parametrized dataset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using simulated data:

.. literalinclude:: ../benchmarks/lasso/datasets/simulated.py

2. Solvers
----------

Solver requires to define a `set_objective` that is constructed
from the union of the data and the objective parameters.

You can define your custom solver.

Example of hand written and parametrized solver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using a hand written solver:

.. literalinclude:: ../benchmarks/lasso/solvers/baseline.py

Example of a solver available from a package on PyPi
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using a package available from PyPi:

.. literalinclude:: ../benchmarks/lasso/solvers/sklearn.py

Example of a solver available from a package available from source
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using a package available from source:

.. literalinclude:: ../benchmarks/lasso/solvers/celer.py

