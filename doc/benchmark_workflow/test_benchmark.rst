.. _test_benchmark:

Testing a benchmark
===================

To ensure that the benchmark is reproducible and can be run by others,
``benchopt`` provides a set of tools to test that the benchmark is properly
formatted and that it can be installed and run easily.
This page describes the various tweaks that can be made to the benchmark tests.

The tests are based on ``pytest``, and can be run with the command:

.. prompt:: bash $

    benchopt test .

This command will run a series of tests to check that the benchmark's components
are compatible with ``benchopt`` and working as expected.


Basic philosophy
~~~~~~~~~~~~~~~~

The test run by ``benchopt test`` will make sure that:

- Checking that all datasets have the proper API and can be loaded.
- Checking that the objective have the proper API and can be computed
  with a simple dataset and the result returned by ``get_one_result``.
- Checking that all solvers have the proper API and can be run on a simple
  configuration.
- Checking that all solvers can be installed in a fresh environment.

The tests that are run can be found in the :ref:`tests_definition`.

By default, if the benchmark has been created using one of our templates, the repo contains some github actions that will try to run these tests on each push/pull request, and once a week, to ensure long term maintainability.

.. Hint::

    The scheduling of the github action run can be changed in
    ``.github/workflows/main.yml``.

Test for Solver run
~~~~~~~~~~~~~~~~~~~

To ensure our third point, benchopt needs to load at least one small dataset
that is compatible with each solver. By default, the benchmark will load a
``Simulated`` dataset, that will be used for testing purposes. The name of this
test dataset can be changed with the ``Objective.test_dataset`` attribute.
As some solvers require different datasets and objective settings to be able to
run, there are two ways to define appropriate configurations:

- In the simulated dataset, one can add the class attribute
``test_parameters``, which stands for a list of parameters that will be tried
to test the solver. For each solver, at least one of these configurations
should be compatible (not skipped).

- The solvers can also provide a ``test_config`` class attribute, which is a dictionary with optional keys ``dataset, objective``. The value of these keys should be a dictionary of parameters for the classes ``Dataset`` and ``Objective``, that will be compatible with the given ``Solver``.


.. _pytest_option:

Specifying options with CLI flags
---------------------------------

It is possible to pass various options to the ``benchopt test`` command,
to customize how the tests are run, in particular in which environment
the tests are executed and in which environment the installation tests are run.

For this command, there are two layers of options that can be specified: the ``benchopt test`` command is a wrapper around the ``pytest`` command,
and some options can be passed to ``benchopt test``, while others are passed to
the underlying ``pytest``. When an option from ``pytest`` is not recognized, and needs to be passed explicitely to the underlying command, it must be separated from the ``benchopt test`` options by a ``--``.

First, the ``benchopt test`` command accepts a ``--env-name`` flag to specify
in which conda environment the tests should be run. If it is not provided, the
test are run in the current environment. If provided, the environment is created
if it does not exist yet and is also used for the installation tests.

Second, extra arguments can be passed to the underlying ``pytest`` command.
Classical ``pytest`` options such as ``-k`` to only run tests that match a given expression, or ``-vs`` for  a more verbose output, can be used.
We also provide extra options for the tests that are run in ``benchopt``:

- ``--test-env=TEST_ENV``: This option is used to specify an environment in
  which the installation tests are run. By default, a fresh environment is
  created for these tests with each run of the ``benchopt test`` command.
  Specifying an environment name here will reuse this environment for next runs.
- ``--skip-install``: Skip test that tries to install solvers. These tests are
  typically slow even when the solvers are installed, which might make it
  complicated to debug some particular issues.
- ``--recreate``: This option forces the recreation of the environment used for
  installation tests even if it already exists.

.. _test_config:

Skipping or xfailing some tests
-------------------------------

In some cases, certain solvers or datasets may not be easily testable on a
continuous integration (CI) service. This is typically the case for very large
datasets, or solvers that require a GPU.
In this case, the tests can be configured to be skipped or marked as expected
to fail (xfailed) for the ``benchopt test`` command.
This can be done by modifying the ``test_config.py`` file, located in the root
folder of the benchmark, and adding a function that skip specific configurations.

Implementing a function named ``check_TESTNAME`` with the same argument as the original test, you can then call ``pytest.xfail`` or ``pytest.skip`` to mark the test appropriately.
For instance, in order to skip the test ``test_solver_install`` for the solver
``solver1`` which is defined in the benchmark, one can add the following
function to the ``test_config.py`` file:

.. code-block:: python

    def check_test_solver_install(benchmark, solver):
        if solver.name == "solver1":
            pytest.skip("Skipping test_solver_install for solver1")
        if solver.name == "solver2":
            pytest.xfail("Known installation error for solver2")

