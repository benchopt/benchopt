.. _test_config:

Testing a benchmark
===================

To ensure that the benchmark are reproducible and can be run by other, ``benchopt`` provides a set of tools to test that the benchmark is properly formatted, and that it can be installed and run easily.
This page describes the various tweaks that can be made to the benchmark tests.


Basic philosophy
----------------

The test run by ``benchopt test`` will make sure that:

1. All classes can be retrieved easily from the benchmark, even when some dependencies are missing.
2. The classes which have dependencies can be properly installed in a new environment and can then be imported.
3. The datasets are compatible with the objective API.
4. The solvers can all be run for a few number of iterations.
5. For convex problem, the tests will also check that the solution is optimal for a small enough problem. This test can be deactivated through setting the ``Objective.is_convex`` flag to ``False``.


Test for Solver run
-------------------

To ensure point 4, ``benchopt`` needs to load at least one small dataset that is compatible with each solver. This is why each benchmark needs to implement at least a ``Simulated`` dataset, that will be used for testing purposes. However, some solvers require different dataset and objective settings to be able to run. There is two way to ensure that a solver can find an appropriate configuration:

- In the simulated dataset, one can add class attribute ``test_parameters``, which stands for a list of parameters that will be tried to test the solver. For each solver, at least one of this configuration should be compatible (not skipped). See benchopt.github.io/how.html#example-of-parametrized-simulated-dataset

- The solvers can also provide a ``test_config`` class attribute, which is a dictionary with optional keys ``dataset, objective``. The value of these key should be a dictionary of parameters for the classes ``Dataset`` and ``Objective``, that will be compatible with the given ``Solver``.


Test configuration
------------------

In some cases, some tests should be ``skip``, or ``xfail`` for a given benchmark. You can configure this for ``benchopt`` using a ``test_config.py`` file at the root of the benchmark. Implementing a function named ``check_TESTNAME`` with the same argument as the original test, you can then call ``pytest.xfail`` or ``pytest.skip`` to mark the test appropriately. For instance, to skip install tests for solver ``XXX``, you can have the following:

.. code:: python

    # test_config.py
    import pytest


    def check_test_solver_install(solver_class):
        if solver_class.name.lower() == 'xxx':
            pytest.skip('XXX is not easy to install automatically.')
