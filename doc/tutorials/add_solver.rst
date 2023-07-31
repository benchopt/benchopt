.. _add_solver:

Add a solver
============

This tutorial walks you through the cornerstones of adding a new solver
to a benchmark. To this end, we will focus on adding ``skglm`` solver to
the L2 logistic regression benchmark.

.. Hint::

    Head to :ref:`get_started` for your first steps with benchopt.


Preliminary
-----------
- solver lives in standalone python file
- solver is class with a name

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
