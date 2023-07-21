.. _run_benchmark:

Run a benchmark
===============

Benchopt offers **two ways** to run a benchmark.
Let's illustrate them on the Benchmark Lasso.
Beforehand, make sure that benchopt is well installed
and the Lasso benchmark is well set up by following the :ref:`get_started`.


With the Command Line Interface (CLI)
-------------------------------------

Directly in the terminal
~~~~~~~~~~~~~~~~~~~~~~~~

It is possible to specify the solvers as well as the datasets
to include in the benchmark run by adding flags after ``benchopt run .``.

For instance, the following command runs the benchmark with solvers
``skglm``, and ``celer`` on leukemia and simulated datasets

.. code-block:: bash

    benchopt run . -s skglm -s celer -d leukemia -d simulated

The flag ``-s`` is to specify a solver whereas ``-d`` is for dataset.

.. note::

    The ``run`` command accepts other flags such ``-j`` to run the benchmark in parallel
    with a given number of processes. Explore that and more with ``benchopt run --help``
    or :ref:`cli_ref`. 

Also, it is possible to specify the parameters of solvers and datasets by wrapping them
in square brackets in comma separate format.

Here is an example to run Proximal Gradient Descent ``Python-PDG`` with acceleration
on simulated data with number of samples ``n_samples`` equals ``100`` and number of features
``n_features`` set to ``20``.

.. code-block:: bash

    benchopt run . -s Python-PGD[use_acceleration=True] -d simulated[n_samples=100,n_features=20]


Using a configuration file
~~~~~~~~~~~~~~~~~~~~~~~~~~

As benchmarks get bigger, it becomes impractical to run benchmarks using flags.
It is here where the configurations files are handy. Using a ``YAML`` file, you
can describe all details of the benchmark run and execute instead

.. code-block:: bash

    benchopt run . --config ./example_config.yml

Here is the look ``example_config.yml`` if we were to run the two previous example into a single one.

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

