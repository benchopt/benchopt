.. _add_solver:

Add a solver
============

This tutorial walks you through the cornerstones of adding a new solver
to a benchmark. To this end, we will focus on adding ``skglm`` solver to
the benchmark Lasso.

.. Hint::

    Head to :ref:`get_started` for your first steps with benchopt.


Preliminary
-----------

A solver is a Python class that lives in a standalone Python file.
It has a unique name that distinguish it from other solvers in the benchmark.

Start by adding a new file ``skglm.py`` to the ``solvers/`` directory.
Notice that we named the python file ``skglm`` as well as the solver,
but we could have chosen anything else.

.. code-block:: python

    from benchopt import BaseSolver, safe_import_context

    with safe_import_context() as import_ctx:
        from skglm import Lasso

    class Solver(BaseSolver):
        name = 'skglm'

To help benchopt with the solver requirements, we enclosed the ``skglm`` module
import in the context manager ``safe_import_context``.


Implementation
--------------
- constructor for getting parameters
- set_objective specify the setup (combination of dataset and objective parameters)
- get_results called by objective to evaluate metrics

Metadata
--------
- install requirements
- docstring for details about the solver

Refinement
----------
- warm_up
- skip
