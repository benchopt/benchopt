.. _get_started:

Get started
===========

Installation
------------

The recommended way to use benchopt is within a conda environment to fully-benefit from all its features.
Hence, start with creating a dedicated conda environment. 

.. code-block:: bash

    # create conda environment with name benchopt
    conda create -n benchopt python

    # activate the environment
    conda activate benchopt

Benchopt is available on PyPi. Run the following command to install the latest **stable version**

.. code-block:: bash

    pip install -U benchopt

Eager to try out the **development version**? you can run instead

.. code-block:: bash

    pip install -U -i https://test.pypi.org/simple/benchopt

.. attention::

   The development version is a work in progress and hence might contain incomplete features.
   A typical user is advised to use the **stable version** instead.

With benchopt being installed, you get access to the :ref:`Command Line Interface (CLI) <cli_ref>`, which enables simple and easy manipulation of benchmarks from the terminal.


Run an existing benchmark
-------------------------

Let's get the first steps with benchopt by comparing solvers of Lasso problem.
Benchopt community maintains :ref:`several optimization benchmarks <available_benchmarks>`.

Start by cloning the Lasso benchmark repository

.. code-block:: bash

    # clone the repository
    git clone https://github.com/benchopt/benchmark_lasso.git

    # access directory
    cd benchmark_lasso

Then install automatically the desired solvers



This package can be installed through `pip`.  In order to allow benchopt to automatically
install solvers dependencies, the install needs to be done in a `conda` environment.


To get the **latest release**, use:

.. prompt:: bash $

    pip install benchopt

And to get the **latest development version**, you can use:

.. prompt:: bash $

    pip install -U -i https://test.pypi.org/simple/ benchopt

This will install the command line tool to run the benchmark. Then, existing
benchmarks can be retrieved from GitHub or created locally. To discover which
benchmarks are presently available look for
`benchmark_* repositories on GitHub <https://github.com/benchopt/>`_,
such as for `Lasso -- l1-regularized linear regression <https://github.com/benchopt/benchmark_lasso>`_.
This benchmark can be retrieved locally with:

.. prompt:: bash $

    git clone https://github.com/benchopt/benchmark_lasso.git



Run existing benchmark
----------------------

This section illustrates benchopt's command line interface on the `Lasso benchmark <https://github.com/benchopt/benchmark_lasso>`_; the syntax is applicable to any benchmark.
All this section assumes that you are in the parent folder of the ``benchmark_lasso`` folder.
The ``--env`` flag specifies that everything is run in the ``benchopt_benchmark_lasso`` ``conda`` environment.

**Installing benchmark dependencies**: benchopt exposes a CLI to install solvers' dependencies automatically.
It only works inside a ``conda`` environment. To install all requirements of the benchmark, make sure a ``conda``
environment is activated and run:

.. prompt:: bash $

    benchopt install --env ./benchmark_lasso

**Run a benchmark**: to run benchmarks on all datasets and with all solvers, run:

.. prompt:: bash $

    benchopt run --env ./benchmark_lasso

The command ``benchopt run`` can also be used outside of a ``conda`` environment without the flag ``-e/--env``.
In that case, the benchmark will only run solvers that are currently installed.

**Run only some solvers and datasets**: to run only the ``sklearn`` and ``celer`` solvers, on the ``simulated`` and ``finance`` datasets, run:

.. prompt:: bash $

    benchopt run --env ./benchmark_lasso -s sklearn -s celer -d simulated -d finance

**Run a solver or dataset with specific parameters**:  some solvers and datasets have parameters; by default all combinations are run.
If you want to run a specific configuration, pass it explicitly, e.g., to run the ``python-pgd`` solver only with its parameter ``use_acceleration`` set to True, use:

.. prompt:: bash $

    benchopt run --env ./benchmark_lasso -s python-pgd[use_acceleration=True]

**Set the number of repetitions**: the benchmark are repeated 5 times by default for greater precision. To run the benchmark 10 times, run:

.. prompt:: bash $

    benchopt run --env ./benchmark_lasso -r 10

**Passing option through configuration file**: all options of ``benchopt run`` can be passed through a YAML configuration file, together with ``--config <configuration_file_name.yml>``.
The options are defined using the same name as the CLI options.
An example of configuration file is:

.. code-block:: yaml

    objective:
      - Lasso Regression[fit_intercept=False,reg=0.5]
    dataset:
      - simulated
      - leukemia
    solver:
      - celer
    force-solver:
      - cd
    n-repetitions: 1

When options are passed both via file and CLI, the CLI takes precedence.

**Getting help**: use

.. prompt:: bash $

    benchopt run -h

to get more details about the different options.
You can also read the :ref:`cli_ref`.
