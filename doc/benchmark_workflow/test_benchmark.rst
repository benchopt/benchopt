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

By default, if the benchmark has been created using one of our templates, the
repo contains some github actions that will try to run these tests on each
push/pull request, and once a week, to ensure long term maintainability.

.. Hint::

    The scheduling of the github action run can be changed in
    ``.github/workflows/main.yml``.

Parameters' configuration for tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, the benchmark will load a ``Simulated`` dataset for testing
purposes. The name of this test dataset can be changed with the
``Objective.test_dataset`` attribute. However, real datasets may be too large
to be used in tests, and some solvers or objectives may require specific
settings — for instance a specific regularization level to be fast, or a
particular data format only possible with a given dataset.
To handle these cases, ``benchopt`` provides a ``test_config`` class attribute
that can be defined on the ``Dataset``, ``Objective``, and ``Solver`` classes.
Each class can override the parameters used to instantiate any of the
component classes during testing:

- ``Dataset.test_config`` directly contains the parameters passed to the
  ``Dataset`` class.
- ``Objective.test_config`` directly contains the parameters passed to the
  ``Objective`` class, with an optional ``dataset`` key whose value is a
  dictionary of parameters that override those of the dataset.
- ``Solver.test_config`` directly contains the parameters passed to the
  ``Solver`` class, with optional ``dataset`` and ``objective`` keys whose
  values are dictionaries of parameters that override those of the dataset
  and objective respectively.

The configurations from the three classes are merged with the following
priority order, from lowest to highest: ``Dataset.test_config``,
``Objective.test_config``, ``Solver.test_config``.

For instance, to require a specific dataset parameter, a specific objective
parameter, and a low number of iteration, one can define:

.. code-block:: python

    class Solver(BaseSolver):
        name = "solver1"

        test_config = {
            'max_iter': 100,
            'objective': {'fit_intercept': False},
            'dataset': {'n_samples': 100, 'n_features': 10},
        }

Or to set a dataset ``my_data`` as the test dataset, with particular
parameters for the whole benchmark:

.. code-block:: python

    class Objective(BaseObjective):
        name = "my objective"
        test_dataset = "my_data"
        test_config = {
            'reg': 0.9,
            'dataset': {'debug': True},
        }

Fallback with ``Dataset.test_parameters``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In addition to ``test_config``, the ``Dataset`` class can expose a
``test_parameters`` class attribute, which is a dictionary of parameters in
the same format as ``parameters`` (see :ref:`parametrized`). Unlike
``test_config``, this is a fallback mechanism only for ``test_solver_run``:
if a solver skips the default test configuration, the parameter combinations
from ``test_parameters`` will be tried in turn, and the test will pass as long
as at least one is compatible with the solver.

.. _pytest_option:

Specifying options with CLI flags
---------------------------------

It is possible to pass various options to the ``benchopt test`` command,
to customize how the tests are run, in particular in which environment
the tests are executed and in which environment the installation tests are run.

For this command, there are two layers of options that can be specified: the ``benchopt test`` command is a wrapper around the ``pytest`` command,
and some options can be passed to ``benchopt test``, while others are passed to
the underlying ``pytest``. When an option from ``pytest`` is not recognized,
and needs to be passed explicitely to the underlying command, it must be
separated from the ``benchopt test`` options by a ``--``.

First, the ``benchopt test`` command accepts a ``--env-name`` flag to specify
in which conda environment the tests should be run. If it is not provided, the
test are run in the current environment. If provided, the environment is created
if it does not exist yet and is also used for the installation tests.

Second, extra arguments can be passed to the underlying ``pytest`` command.
Classical ``pytest`` options such as ``-k`` to only run tests that match a
given expression, or ``-vs`` for  a more verbose output, can be used.
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
folder of the benchmark, and adding a function that skip specific
configurations.

Implementing a function named ``check_TESTNAME`` with the same argument as the
original test, you can then call ``pytest.xfail`` or ``pytest.skip`` to mark
the test appropriately.
For instance, in order to skip the test ``test_solver_install`` for the solver
``solver1`` which is defined in the benchmark, one can add the following
function to the ``test_config.py`` file:

.. code-block:: python

    def check_test_solver_install(benchmark, solver):
        if solver.name == "solver1":
            pytest.skip("Skipping test_solver_install for solver1")
        if solver.name == "solver2":
            pytest.xfail("Known installation error for solver2")

