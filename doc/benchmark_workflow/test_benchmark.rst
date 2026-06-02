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

- all datasets have a valid API and can be loaded.
- the objective has a valid API and can be computed
  with a simple dataset and the result returned by ``get_one_result``.
- all solvers have a valid API and can be run on a simple
  configuration.
- all solvers can be installed in a fresh environment.
- the benchmark's ``config.yml`` is valid.

By default, if the benchmark has been created using one of our templates, the
repo contains some github actions that will try to run these tests on each
push/pull request, and once a week, to ensure long term maintainability.

.. Hint::

    The scheduling of the github action run can be changed in
    ``.github/workflows/main.yml``.

Tests reference
~~~~~~~~~~~~~~~

The full set of pytest checks run by ``benchopt test`` (parametrized over
the benchmark's datasets and solvers where applicable) is:

- ``test_dataset_class[<dataset>]`` — the dataset class exposes the
  expected public API (``name``, callable ``get_data``).
- ``test_dataset_get_data[<dataset>]`` — each installed dataset's
  ``get_data`` returns a dictionary, as expected by the objective.
- ``test_benchmark_objective[<test_dataset>]`` — the objective instantiates
  on the resolved test dataset and the output of ``Objective.__call__``
  on ``get_one_result`` has the expected schema.
- ``test_benchmark_config_validity`` — the benchmark's ``config.yml``
  only uses valid options.
- ``test_solver_class[<solver>]`` — the solver class exposes the
  expected public API (``name``, optional ``sampling_strategy``,
  ``stopping_criterion``, or ``get_next``).
- ``test_solver_install_api[<solver>]`` — the solver declares a known
  install command (``None``, ``'conda'`` or ``'shell'``).
- ``test_solver_install[<solver>]`` — the solver installs cleanly in a
  fresh conda environment (skipped under ``--skip-install``).
- ``test_solver_stopping_criterion[<solver>-<test_dataset>]`` — the solver's
  ``stopping_criterion`` is compatible with the objective (only useful for
  iterative evaluation benchmark).
- ``test_solver_run[<solver>-<test_dataset>]`` — the solver runs on at least
  one configuration of the resolved test datasets.

The full definition of the tests that are run can be found in the
:ref:`tests_definition`.

Note that several of these tests are parametrized over the benchmark's datasets
and solvers, and that the test parameters used for all components, as well as
the ``test_dataset(s)`` used for testing the objective and solver runs can be
configured (see below).

Parameters' configuration for tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The test bed used for ``test_solver_run`` and ``test_benchmark_objective``
is controlled by a ``test_config`` class attribute that can be defined on
the ``Dataset``, ``Objective``, and ``Solver`` classes. Each class can
override the parameters used to instantiate any of the component classes
during testing, and the ``dataset`` entry of ``test_config`` can select
which dataset class is used:

- ``Dataset.test_config`` directly contains the parameters passed to the
  ``Dataset`` class.
- ``Objective.test_config`` directly contains the parameters passed to the
  ``Objective`` class, with an optional ``dataset`` key whose value is a
  dictionary of parameters that override those of the dataset. A special
  ``name`` entry inside that ``dataset`` dictionary selects which dataset
  class is used for testing — and it may be a list of names, in which case
  ``test_benchmark_objective`` is run once per name (useful for objectives
  whose code path differs across datasets, e.g. forecasting vs.
  classification).
- ``Solver.test_config`` directly contains the parameters passed to the
  ``Solver`` class, with optional ``dataset`` and ``objective`` keys whose
  values are dictionaries of parameters that override those of the dataset
  and objective respectively. A ``name`` parameter in ``dataset`` behaves
  similarly to the one in  ``Objective.test_config``.
If none of these is set, the benchmark falls back to ``Objective.test_dataset_name``,
which in turn default to ``Simulated``. Configuring such ``test_dataset`` is
necessary to allow testing the benchmark automatically.

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
        test_config = {
            'reg': 0.9,
            'dataset': {'name': 'my_data', 'debug': True},
        }

For a multi-task benchmark, a solver that only supports a subset of the
datasets can declare which one(s) to test against:

.. code-block:: python

    class Solver(BaseSolver):
        name = "classifier1"

        test_config = {
            'dataset': {'name': 'data1'},  # or ['data_a', 'data_b']
        }

Note that configuring an empty list of test datasets raises a
``ValueError`` at collection time.

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

