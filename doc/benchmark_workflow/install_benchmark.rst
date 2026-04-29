.. _install_benchmark:

Install a benchmark
======================

In order to make it easy to run a new benchmark, benchopt provides an interface
to specify and install requirements for the various components of the benchmarks.

- By default, calling ``benchopt install .`` will install the requirements for the
  benchmark, including all solvers and datasets, using the ``conda-forge`` channel.

- The minimum requirements to run the benchmark are specified in
  ``objective.py``. They can be installed using the command
  ``benchopt install --minimal``.

- The requirements that are specific to each ``Dataset/Solver`` can be
  specified in each class, and they can be installed individually by selecting
  the proper component using ``benchopt install -d dataset1 -s solver1``.

- Finally, it is possible to prepare the datasets prior to running the
  benchmark.  See :ref:`prepare_datasets` below for details.


.. _prepare_datasets:

Preparing datasets
------------------

Benchopt separates **data preparation** (heavy one-time work: downloads,
extraction, pre-processing) from **data loading** (fast, per-run work done
by ``get_data()``).

Preparation is triggered by the dedicated command::

    $ benchopt prepare path/to/benchmark

Benchopt calls the ``prepare()`` method of every dataset (see
:ref:`write_benchmark` for how to implement it) and caches the result with
`joblib`, so re-running the command is a no-op when nothing has changed.
Use ``--force`` to bypass the cache and re-run preparation unconditionally.

Preparation can also be triggered right after installing the benchmark
dependencies with the ``--prepare`` flag::

    $ benchopt install path/to/benchmark --prepare

This is convenient in CI pipelines or when setting up a benchmark on a
remote server where internet access may not be available at run time.

.. note::

    The ``--download`` option of ``benchopt install`` is deprecated in
    favour of ``benchopt install --prepare``.

Preparation can also be parallelised across datasets using the same options as
:ref:`benchopt run <parallel_run>`:

.. code-block:: bash

    # Prepare all datasets on 8 local workers
    benchopt prepare path/to/benchmark -j 8

    # Prepare using a distributed backend (Dask, SLURM via submitit, …)
    benchopt prepare path/to/benchmark --parallel-config slurm_config.yml

See :ref:`parallel_run` for how to write a ``parallel_config.yml`` and for the
full list of supported backends.


.. _specify_requirements:

Specifying requirements
-----------------------

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
---------------------------

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

