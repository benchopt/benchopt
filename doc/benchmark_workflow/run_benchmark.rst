.. _run_benchmark:

Run a benchmark
===============

Benchopt offers **two ways** to run a benchmark.
Let's illustrate them on the Lasso benchmark.
Beforehand, make sure that benchopt is installed and the Lasso benchmark is set up by following the instructions in :ref:`get_started`.


With the Command Line Interface (CLI)
-------------------------------------

Directly in the terminal
~~~~~~~~~~~~~~~~~~~~~~~~

It is possible to specify the solvers as well as the datasets
to include in the benchmark run by using flags after ``benchopt run .``.

For instance, the following command runs the benchmark with solvers
``skglm`` and ``celer``, on datasets "leukemia" and "simulated".

.. code-block:: bash

    benchopt run . -s skglm -s celer -d leukemia -d simulated

The ``-s`` flag is to specify a solver whereas ``-d`` specifies the dataset. To include multiple datasets, we use multiple ``-d`` flags.

.. note::

    The ``run`` command accepts other flags such ``-j`` to run the benchmark in parallel with a given number of processes.
    The list of flags is available through ``benchopt run --help`` or in the :ref:`cli_ref` page .

In addition, it is possible to specify the parameters of solvers and datasets by wrapping them in square brackets in comma separated format.

Here is an example to run Proximal Gradient Descent (``Python-PGD``) with acceleration on simulated data with number of samples ``n_samples`` equal ``100`` and number of features ``n_features`` set to ``20``.

.. code-block:: bash

    benchopt run . -s Python-PGD[use_acceleration=True] -d simulated[n_samples=100,n_features=20]


.. _run_with_config_file:

Using a configuration file
~~~~~~~~~~~~~~~~~~~~~~~~~~

As benchmarks get bigger, it becomes impractical to run benchmarks using flags.
It is here where configurations files are handy. Using a ``YAML`` file, you
can describe all details of the benchmark run and afterward execute

.. code-block:: bash

    benchopt run . --config ./example_config.yml

Here is the look the configuration file ``example_config.yml`` if we were to run the two previous example into a single one.

.. code-block:: yml

    solver:
        - skglm
        - celer
        - python-pgd[use_acceleration=True]

    dataset:
        - leukemia
        - simulated[n_samples=100,n_features=20]


With a Python script
--------------------

Another way to run a benchmark is via a Python script.
Typical use-cases of that are

- Automating the run of several benchmarks
- Using ``vscode`` debugger where the python script serves as an entry point to benchopt internals

The following script illustrate running the :ref:`previous example <run_with_config_file>`.
It assume that the python script is located at the same level as the benchmark folder.

.. code-block:: python

    from benchopt import run_benchmark
    from benchopt.benchmark import Benchmark

    # load benchmark
    BENCHMARK_PATH = "./"
    benchmark = Benchmark(BENCHMARK_PATH)

    # run benchmark
    run_benchmark(
        benchmark,
        solver_names=[
            "skglm",
            "celer",
            "python-pgd[use_acceleration=True]",
        ],
        dataset_names=[
            "leukemia",
            "simulated[n_samples=100,n_features=20]"
        ],
    )

.. note::

    Learn more about the different parameters supported by ``run_benchmark``
    function on :ref:`API references <API_ref>`.
