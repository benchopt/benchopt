.. _class_customization:

Benchmark class configuration
=============================

This page covers the class attributes and optional methods that are common to
all three benchmark components (``Dataset``, ``Objective``, ``Solver``):
exposing parameter grids, declaring dependencies, and hooking into the
benchmark lifecycle.


.. _parametrized:

Parametrization
---------------

Benchmark classes can expose several configurations through a class attribute
named ``parameters``. This applies to the concrete ``Objective``, ``Dataset``,
and ``Solver`` classes that inherit from :class:`benchopt.BaseObjective`,
:class:`benchopt.BaseDataset`, and :class:`benchopt.BaseSolver`.

The expected format is a dictionary whose keys are parameter names and whose
values are lists of candidate values:

.. code-block:: python

   class Dataset(BaseDataset):
       name = "simulated"
       parameters = {
           "n_samples": [100, 1000],
           "n_features": [20, 50],
       }

``benchopt`` evaluates the cartesian product of these values. In the example
above, the dataset is instantiated for the four combinations of
``n_samples`` and ``n_features``.

For each instantiated configuration, the selected values are stored as class
attributes, so they can be accessed as ``self.n_samples``, ``self.n_features``,
and so on inside the class methods. They are also included in the displayed
name of the instance.

When some parameters should vary together instead of being combined through a
cartesian product, they can be grouped in a single key with comma-separated
parameter names. In that case, the corresponding values must be tuples with
the same arity:

.. code-block:: python

   class Dataset(BaseDataset):
       name = "simulated"
       parameters = {
           "n_samples, n_features": [(100, 20), (1000, 50)],
           "reg": [0.1, 1.0],
       }

This keeps ``n_samples`` and ``n_features`` paired together, while still
forming the cartesian product with ``reg``.

Parameters can be overridden directly from the command line when selecting an
objective, dataset, or solver:

.. prompt:: bash $

   benchopt run . \
       -o objective[reg=0.1] \
       -d simulated[n_samples=100,n_features=[20,50]] \
       -s my-solver[use_acceleration=True]

The values in brackets use Python literal syntax, so booleans, strings,
numbers, ``None``, lists, or tuples can be passed. An override can be:

- a single value, such as ``reg=0.1``;
- a list of values, such as ``n_features=[20,50]``;
- a grouped parameter selection, such as
  ``'n_samples, n_features'=[(100, 20), (1000, 50)]``.

Only the parameters specified in the selector are replaced. All unspecified
parameters keep the values defined in the class-level ``parameters``
dictionary. The resulting run configurations are then generated from the
cartesian product of the remaining values.

For more complex experiment definitions, the same parameter overrides can be
expressed in the run configuration file described in
:ref:`Run a benchmark <run_benchmark>`.

.. _managing_dependencies:

Managing dependencies
---------------------

Benchopt uses conda environments to isolate each benchmark's dependencies.
This page explains how to declare what each component needs and how to
control the Python version of the environment.

.. _specify_requirements:

Specifying requirements
~~~~~~~~~~~~~~~~~~~~~~~

To specify how dependencies should be installed, you can use the ``install_cmd`` class attribute.
This attribute accepts two possible values:

  1. ``conda`` (default): Dependencies will be installed using Conda. In this case, you should
  specify the required dependencies in the ``requirements`` class attribute. Note that
  dependencies to install with ``pip`` are also specified with this option.

  2. ``shell``: This option allows you to provide a custom shell script for installing dependencies.
  When using this value, you need to set the ``install_script`` class attribute to the path of your shell script.
  Benchopt will execute this script in the shell and pass the Conda environment directory as an argument.


By properly setting these attributes, you ensure that all dependencies are installed
correctly. This will help users to run your benchmarks without any issues.

Examples:

.. code-block:: python

  requirements = ['pkg']  # conda package `pkg`
  requirements = ['chan::pkg']  # package `pkg` in conda channel `chan`


One might also need to install pip packages. This can be done by using the
channel `pip` and the `conda` installer. The syntax is the following:

.. code-block:: python

  install_cmd = 'conda'  # optional
  requirements = ['pip::pkg']  # pip package `pkg`


.. _specify_python_version:

Specifying a Python version
~~~~~~~~~~~~~~~~~~~~~~~~~~~

When benchopt creates a conda environment, it uses Python 3.12 by default.
If a benchmark requires a specific Python version, it can be declared via
the ``python_version`` class attribute on the ``Objective``.
Both an exact minor version and a PEP-440 specifier are accepted:

.. code-block:: python

    class Objective(BaseObjective):
        name = "my-benchmark"
        python_version = "3.11"    # exact: conda env will use Python 3.11.x
        # python_version = ">=3.11"  # specifier: any Python >= 3.11 is accepted
        ...

When running ``benchopt install --env-name myenv``, benchopt will:

- **Create** the conda env with the requested Python version if it does not
  exist yet. An exact version (e.g. ``"3.11"``) pins the minor version;
  a specifier (e.g. ``">=3.11"``) lets conda pick the newest compatible
  release.
- **Warn** if the env already exists but its Python version does not satisfy
  the constraint declared in the objective, so that users can recreate the
  env with ``--recreate`` if needed.

If ``python_version`` is not set, the default version (3.12) is used.


.. _benchopt_hooks:

Optional methods and hooks
--------------------------

All benchmark classes expose optional methods to customise the workflow.

**BaseDataset**

- :func:`benchopt.BaseDataset.prepare`: expensive one-time preparation
  (downloads, extraction, preprocessing) cached by joblib. List parameter
  names that do not affect preparation in ``prepare_cache_ignore`` to avoid
  redundant runs. Triggered via :ref:`benchopt prepare <prepare_datasets>`.

**BaseObjective**

- :func:`benchopt.BaseObjective.skip`: called before ``set_data`` to skip
  dataset/objective combinations that are incompatible. Takes the same
  arguments as ``set_data``.

- :func:`benchopt.BaseObjective.get_one_result`: returns a dummy result dict
  used by ``benchopt test`` to validate metric computation. Optional — if not
  implemented, the test-time metric validation step is silently skipped.

- :func:`benchopt.BaseObjective.save_final_results`: called after the last
  run for each solver to persist artefacts (models, arrays, …) as a ``.pkl``
  file alongside the parquet results.

**BaseSolver**

- :func:`benchopt.BaseSolver.skip`: called before ``set_objective`` to skip
  solver/objective combinations that are incompatible. Takes the same arguments
  as ``set_objective``. Refer to :ref:`Advanced usage <skipping_solver>` for an
  example.

- :func:`benchopt.BaseSolver.warm_up`: called once before timed runs. Use
  ``Solver.run_once()`` here to absorb JIT compilation costs without
  impacting timings.

- :func:`benchopt.BaseSolver.pre_run_hook`: called before each ``run`` with
  the same ``stop_val``; useful for JAX precompilation over varying iteration
  counts.

- :func:`benchopt.BaseSolver.get_next`: overrides the default logarithmic
  ``stop_val`` schedule. Refer to :ref:`Advanced usage <sampling_strategy>`
  for an example.
