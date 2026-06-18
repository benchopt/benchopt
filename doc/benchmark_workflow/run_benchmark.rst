.. _run_benchmark:
.. _install_benchmark:

Install and run a benchmark
============================

Installing a benchmark
-----------------------

Benchopt provides ``benchopt install`` to set up all dependencies in a
dedicated conda environment:

- ``benchopt install .`` installs requirements for all solvers and datasets
  using the ``conda-forge`` channel.
- ``benchopt install . --minimal`` installs only the minimum requirements
  declared in ``objective.py``.
- ``benchopt install . -d dataset1 -s solver1`` installs only the requirements
  for selected components.
- ``benchopt install . --prepare`` also runs :ref:`dataset preparation
  <prepare_datasets>` after installing — convenient for CI or remote servers
  without internet access at run time.

See :ref:`managing_dependencies` for how to declare requirements and control
the Python version when writing a benchmark.


.. _prepare_datasets:

Preparing datasets
------------------

Benchopt separates **data preparation** (heavy one-time work: downloads,
extraction, pre-processing) from **data loading** (fast, per-run work done
by ``get_data()``).

Preparation is triggered by the dedicated command::

    $ benchopt prepare path/to/benchmark

Benchopt calls the :func:`~benchopt.BaseDataset.prepare()` method of every
dataset and caches the result with `joblib`, so re-running the command is a
no-op when nothing has changed. Use ``--force`` to bypass the cache and re-run
preparation unconditionally.

Preparation can also be parallelised across datasets using the same options as
:ref:`benchopt run <parallel_run>`.


Running a benchmark
-------------------

Once installed, run the benchmark with ``benchopt run .``.
With the :ref:`cli_ref`, there are two ways to run a benchmark: passing options with flags in the CLI, or with a configuration file.

Each ``solver/dataset`` define in the benchmark repository is automatically
detected and included in the run. To list all available solvers and datasets, use ``benchopt info .``.

.. prompt:: bash $

    benchopt info .

.. code-block:: console

    Info regarding the benchmark 'my_bench'
    ----------
    # DATASETS
    dataset1, dataset2, dataset3, ...
    ----------
    # SOLVERS
    solver1, solver2, solver3, ...
    ----------


Specifying options with CLI flags
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is possible to select which solvers as well as the datasets
to include in the benchmark run by using flags after ``benchopt run .``.

For instance, the following command runs the benchmark with solvers
``solver1`` and ``solver2``, on datasets ``dataset1`` and ``dataset3``.

.. prompt:: bash $

    benchopt run . -s solver1 -s solver2 -d dataset1 -d dataset3

The ``-s`` flag is to specify a solver whereas ``-d`` specifies a dataset.
To include multiple datasets/solvers, use multiple ``-d``/``-s`` flags, as in the above snippet.

.. note::

    The ``run`` command accepts other flags such as ``-j`` to run the benchmark in parallel with a given number of processes.
    The list of flags is available through ``benchopt run --help`` or in the :ref:`cli_ref` page.

In addition, it is possible to specify the parameters of solvers and datasets by wrapping them in square brackets in comma separated format.

The following snippet runs the ``solver1`` solver with its ``p1`` parameter set
to ``1``, on the ``dataset1`` dataset.
This dataset has parameters ``n_samples`` and ``n_features`` that we set to ``100`` and ``20`` respectively.

.. tab-set::

    .. tab-item:: shell

        .. prompt:: bash $

            benchopt run . -s solver1[p1=1] -d dataset1[n_samples=100,n_features=20]

    .. tab-item:: zsh

        .. prompt:: bash $

            benchopt run . -s "solver1[p1=1]" -d "dataset1[n_samples=100,n_features=20]"

.. note::

    If a parameter of a solver/dataset is not explicitly set via CLI, benchopt uses all its values specified in the code.

.. _run_with_config_file:

Using a configuration file
~~~~~~~~~~~~~~~~~~~~~~~~~~

When using a complex configuration, it is more handy to specify it through a configuration file.
Using a YAML file and the ``--config`` flag, it is possible to describe all details of the benchmark run and execute instead

.. prompt:: bash $

    benchopt run . --config ./example_config.yml

Here is the content of configuration file ``example_config.yml`` if we were to run the two previous examples into a single one.

.. code-block:: yaml

    solver:
        - solver1
        - solver2
        - solver3[p1=1]

    dataset:
        - dataset3
        - dataset1[n_samples=100,n_features=10]
        - dataset1:
            n_samples: 100
            n_features: [20, 30]
        - dataset1:
            n_samples, n_features: [[200, 20], [150, 30]]


.. _run_benchmark_with_py_script:

Run a benchmark using a Python script
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Another way to run a benchmark is via a Python script.
Typical use-cases of that are

- Automating the run of several benchmarks
- Using ``vscode`` debugger where the python script serves as an entry point to benchopt internals

The following script illustrates running the :ref:`benchmark Lasso <run_with_config_file>`.
It assumes that the python script is located at the same level as the benchmark folder.

.. code-block:: python

    from benchopt import run_benchmark


    # run benchmark
    run_benchmark(
        benchmark_path='.',
        solver_names=[
            "solver1",
            "solver2",
            "solver3[p1=1]",
        ],
        dataset_names=[
            "dataset3",
            "dataset1[n_samples=100,n_features=20]"
        ],
    )

.. note::

    Learn more about the different parameters supported by ``run_benchmark``
    function on :ref:`API references <API_ref>`.


.. _run_caching:

Caching solver runs
~~~~~~~~~~~~~~~~~~~

Each solver/dataset/objective combination is cached on disk (via joblib,
in the ``__cache__/`` folder of the benchmark) so that re-running
``benchopt run`` skips any combination whose result is already stored.
The cache is **invalidated automatically** when the source code of the
solver, objective, or dataset changes.
The default cache location (``__cache__/`` inside the benchmark folder) can be
changed by setting the ``cache`` key in the global benchopt config file —
see :ref:`benchopt_config_settings`.

Useful flags:

- ``-f SOLVER_NAME`` (``--force-solver``) — re-run a specific solver even if
  its result is cached, e.g. ``benchopt run . -f skglm``.
- ``--no-cache`` — disable caching entirely; every combination is always run
  from scratch.
- ``--collect`` — skip all computation and only collect results that are
  already in the cache into a result file.
