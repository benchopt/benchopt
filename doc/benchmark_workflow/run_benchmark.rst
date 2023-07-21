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
skglm, and celer on leukemia and simulated datasets

.. code-block:: bash

    benchopt run . -s skglm -s celer -d leukemia -d simulated

The flag ``-s`` is to specify a solver whereas ``-d`` is for dataset.

.. note::

    The ``run`` command accepts other flags such ``-j`` to run the benchmark in parallel
    with a given number of processes. Explore that and more with ``benchopt run --help``
    or :ref:`cli_ref`. 


Using a configuration file
~~~~~~~~~~~~~~~~~~~~~~~~~~



With a Python script
--------------------

