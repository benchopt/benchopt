.. _run_benchmark:

Run a benchmark
===============

Let's use the Lasso benchmark to illustrate ways of running a benchmark.

.. Hint::

    Head to :ref:`get_started` to first install benchopt
    and setup the Lasso benchmark.

With the :ref:`cli_ref`, there are two ways to run a benchmark: passing options with flags in the CLI, or with a configuration file.

Specifying options with CLI flags
---------------------------------

It is possible to specify the solvers as well as the datasets
to include in the benchmark run by using flags after ``benchopt run .``.

For instance, the following command runs the benchmark with solvers
``skglm`` and ``celer``, on datasets ``leukemia`` and ``simulated``.

.. prompt:: bash $

    benchopt run . -s skglm -s celer -d leukemia -d simulated

The ``-s`` flag is to specify a solver whereas ``-d`` specifies a dataset.
To include multiple datasets/solvers, use multiple ``-d``/``-s`` flags, as in the above snippet.

.. note::

    The ``run`` command accepts other flags such as ``-j`` to run the benchmark in parallel with a given number of processes.
    The list of flags is available through ``benchopt run --help`` or in the :ref:`cli_ref` page.

In addition, it is possible to specify the parameters of solvers and datasets by wrapping them in square brackets in comma separated format.

The following snippet runs the ``Python-PGD`` solver with its acceleration parameter set to ``True``, on the ``simulated`` dataset.
This dataset has parameters ``n_samples`` and ``n_features`` that we set to ``100`` and ``20`` respectively.

.. tab-set::

    .. tab-item:: shell

        .. prompt:: bash $

            benchopt run . -s Python-PGD[use_acceleration=True] -d simulated[n_samples=100,n_features=20]

    .. tab-item:: zsh

        .. prompt:: bash $

            benchopt run . -s "Python-PGD[use_acceleration=True]" -d "simulated[n_samples=100,n_features=20]"

.. note::

    If a parameter of a solver/dataset is not explicitly set via CLI, benchopt uses all its values specified in the code.

.. _run_with_config_file:

Using a configuration file
--------------------------

When using a complex configuration, it is more handy to specify it through a configuration file.
Using a YAML file and the ``--config`` flag, it is possible to describe all details of the benchmark run and execute instead

.. prompt:: bash $

    benchopt run . --config ./example_config.yml

Here is the content of configuration file ``example_config.yml`` if we were to run the two previous examples into a single one.

.. code-block:: yaml

    solver:
        - skglm
        - celer
        - python-pgd[use_acceleration=True]

    dataset:
        - leukemia
        - simulated[n_samples=100,n_features=10]
        - simulated:
            n_samples: 100
            n_features: [20, 30]
        - simulated:
            n_samples, n_features: [[200, 20], [150, 30]]

.. note::

    A third, less frequent, option to run a benchmark is using a Python script.
    Check it out on :ref:`advanced usage <run_benchmark_with_py_script>`.


.. _run_benchmark_with_py_script:

Run a benchmark using a Python script
-------------------------------------

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
