Benchopt: Benchmark repository for optimization
===============================================

|Test Status| |Python 3.6+| |codecov|

Benchopt is a package to make the comparison of optimizations algorithms simple, transparent and reproducible.

It is written in Python but is available with
`many programming languages <auto_examples/plot_run_benchmark_python_R.html>`_.
So far it has been tested with `Python <https://www.python.org/>`_,
`R <https://www.r-project.org/>`_, `Julia <https://julialang.org/>`_
and compiled binaries written in C/C++ available via a terminal
command.
If a solver can be installed via
`conda <https://docs.conda.io/en/latest/>`_, it should just work in benchopt!

Benchopt is used through a command line as documented
in the :ref:`cli_documentation`.
Once benchopt is installed, running and replicating an optimization benchmark is **as simple as doing**:

.. prompt:: bash $

    git clone https://github.com/benchopt/benchmark_logreg_l2
    benchopt install --env ./benchmark_logreg_l2
    benchopt run --env ./benchmark_logreg_l2

Running these commands will fetch the benchmark files, install the benchmark
requirements in a dedicated environment called ``benchopt_benchmark_logreg_l2`` and
give you a benchmark plot on l2-regularized logistic regression:

.. figure:: auto_examples/images/sphx_glr_plot_run_benchmark_003.png
   :target: how.html
   :align: center
   :scale: 80%


Install
--------

This package can be installed through `pip`.  In order to allow benchopt to automatically
install solvers dependencies, the install needs to be done in a `conda` environment.

.. prompt:: bash $

    conda create -n benchopt python
    conda activate benchopt

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

Run a benchmark
---------------

This section illustrates benchopt's command line interface on the `Lasso benchmark <https://github.com/benchopt/benchmark_lasso>`_; the syntax is applicable to any benchmark.
All this section assumes that you are in the parent folder of the ``benchmark_lasso`` folder.
The ``--env`` flag specifies that everything is run in the ``benchopt_benchmark_lasso`` ``conda`` environment.

**Installing benchmark dependencies**: ``benchopt`` exposes a CLI to install solvers' dependencies automatically.
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

    objective-filter:
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
You can also read the :ref:`cli_documentation`.

Benchmark results
-----------------

All the public benchmark results are available at `Benchopt Benchmarks results <https://benchopt.github.io/results/>`_.

**Publish results**: You can directly publish the result of a run of ``benchopt`` on `Benchopt Benchmarks results <https://benchopt.github.io/results/>`_. You can have a look at this page to :ref:`publish_doc`.



Frequently asked questions (FAQ)
================================

Write a benchmark
-----------------

Learn how to :ref:`how`, including creating an objective, a solver, and
a dataset.

Performance curve construction
------------------------------

The goal of ``benchopt`` is to evaluate the evolution of a method's performance with respect to its computational budget.
For evaluating this, ``benchopt`` allows to vary the computational budget for both black-box solvers and solvers that allow for callbacks. Learn :ref:`performance_curves`. Note that the budget varying strategy can also be configured on a per-solver basis, as described in: :ref:`sampling_strategy`.

Re-using code in a benchmark
----------------------------

For some solver and datasets, it is necessary to share some operations or pre-processing steps. Benchopt allows to factorize this code by :ref:`benchmark_utils_import`.

Parallel run
------------

Benchopt allows to run different benchmarked methods in parallel, either with ``joblib`` using ``-j 4`` to run on multiple CPUs of a single machine or using SLURM, as described in :ref:`slurm_run`.


Citing Benchopt
---------------

If you use ``Benchopt`` in a scientific publication, please cite the following paper

.. code-block:: bibtex

   @inproceedings{benchopt,
      author = {Moreau, Thomas and Massias, Mathurin and Gramfort, Alexandre and Ablin, Pierre
                and Bannier, Pierre-Antoine and Charlier, Benjamin and Dagréou, Mathieu and Dupré la Tour, Tom
                and Durif, Ghislain and F. Dantas, Cassio and Klopfenstein, Quentin
                and Larsson, Johan and Lai, En and Lefort, Tanguy and Malézieux, Benoit
                and Moufad, Badr and T. Nguyen, Binh and Rakotomamonjy, Alain and Ramzi, Zaccharie
                and Salmon, Joseph and Vaiter, Samuel},
      title  = {Benchopt: Reproducible, efficient and collaborative optimization benchmarks},
      year   = {2022},
      booktitle = {NeurIPS},
      url    = {https://arxiv.org/abs/2206.13424}
   }

Other functionalities
---------------------

- Some solvers are not compatible with certain datasets or objective configurations. This can be accommodated by :ref:`skiping_solver`.
- For some solvers, it is necessary to cache some pre-compilation for fair benchmarks. This can easily be done with benchopt, as described in :ref:`precompilation`.


.. include:: contrib.rst

.. include:: benchmark_list.rst

Website contents
================

.. toctree::
   :maxdepth: 1

   cli
   api
   how
   publish
   config
   advanced
   whats_new
   Fork benchopt on Github <https://github.com/benchopt/benchopt>

.. |Test Status| image:: https://github.com/benchopt/benchopt/actions/workflows/test.yml/badge.svg
   :target: https://github.com/benchopt/benchopt/actions/workflows/test.yml
.. |Python 3.6+| image:: https://img.shields.io/badge/python-3.6%2B-blue
   :target: https://www.python.org/downloads/release/python-360/
.. |codecov| image:: https://codecov.io/gh/benchopt/benchopt/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/benchopt/benchopt
