.. _run_benchmark:

Run a benchmark
===============

Let's use the Lasso benchmark to illustrate ways of running a benchmark.
Beforehand, make sure that benchopt is installed and the Lasso benchmark is set up by following the instructions in :ref:`get_started`.

With the :ref:`cli_ref`, there are two options

Directly in the terminal
------------------------

It is possible to specify the solvers as well as the datasets
to include in the benchmark run by using flags after ``benchopt run .``.

For instance, the following command runs the benchmark with solvers
``skglm`` and ``celer``, on datasets "leukemia" and "simulated".

.. prompt:: bash $

    benchopt run . -s skglm -s celer -d leukemia -d simulated

The ``-s`` flag is to specify a solver whereas ``-d`` specifies the dataset.
To include multiple datasets/solvers, use multiple ``-d``/ ``-s`` flags.

.. note::

    The ``run`` command accepts other flags such ``-j`` to run the benchmark in parallel with a given number of processes.
    The list of flags is available through ``benchopt run --help`` or in the :ref:`cli_ref` page .

In addition, it is possible to specify the parameters of solvers and datasets by wrapping them in square brackets in comma separated format.

Here is an example to run Proximal Gradient Descent (``Python-PGD``) with acceleration on simulated data with number of samples ``n_samples`` equal ``100`` and number of features ``n_features`` set to ``20``.

.. prompt:: bash $

    benchopt run . -s Python-PGD[use_acceleration=True] -d simulated[n_samples=100,n_features=20]


.. _run_with_config_file:

Using a configuration file
--------------------------

It is more handy to launch a benchmark run with many parameters using a configuration file.
Using a YAML file, it is possible to describe all details of the benchmark run and execute instead

.. prompt:: bash $

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
