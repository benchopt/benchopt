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

Write a benchmark
-----------------

Learn how to :ref:`how`, including creating an objective, a solver, and
a dataset.


Available benchmarks
--------------------

.. note::
    Some benchmarks are briefly described in the list below. For a complete
    list of benchmarks, see GitHub repositories of the form `benchopt/benchmark_*
    <https://github.com/orgs/benchopt/repositories?q=benchmark_&type=all&language=&sort=stargazers/>`_.

**Notation:**  In what follows, n (or n_samples) stands for the number of samples and p (or n_features) stands for the number of features.

.. math::

 y \in \mathbb{R}^n, X = [x_1^\top, \dots, x_n^\top]^\top \in \mathbb{R}^{n \times p}

- `Ordinary Least Squares (OLS) <https://github.com/benchopt/benchmark_ols>`_: |Build Status OLS|

.. math::

    \min_w \frac{1}{2} \|y - Xw\|^2_2

- `Non-Negative Least Squares (NNLS) <https://github.com/benchopt/benchmark_nnls>`_: |Build Status NNLS|

.. math::

    \min_{w \geq 0} \frac{1}{2} \|y - Xw\|^2_2

- `LASSO: L1-regularized least squares <https://github.com/benchopt/benchmark_lasso>`_: |Build Status Lasso|

.. math::

    \min_w \frac{1}{2} \|y - Xw\|^2_2 + \lambda \|w\|_1

- `L2-regularized logistic regression <https://github.com/benchopt/benchmark_logreg_l2>`_: |Build Status LogRegL2|

.. math::

    \min_w \sum_{i=1}^{n} \log(1 + \exp(-y_i x_i^\top w)) + \frac{\lambda}{2} \|w\|_2^2

- `L1-regularized logistic regression <https://github.com/benchopt/benchmark_logreg_l1>`_: |Build Status LogRegL1|

.. math::

    \min_w \sum_{i=1}^{n} \log(1 + \exp(-y_i x_i^\top w)) + \lambda \|w\|_1

- `L2-regularized Huber regression <https://github.com/benchopt/benchmark_huber_l2>`_: |Build Status HuberL2|

.. math::

  \min_{w, \sigma} {\sum_{i=1}^n \left(\sigma + H_{\epsilon}\left(\frac{X_{i}w - y_{i}}{\sigma}\right)\sigma\right) + \lambda {\|w\|_2}^2}

where

.. math::

  H_{\epsilon}(z) = \begin{cases}
         z^2, & \text {if } |z| < \epsilon, \\
         2\epsilon|z| - \epsilon^2, & \text{otherwise}
  \end{cases}

- `L1-regularized quantile regression <https://github.com/benchopt/benchmark_quantile_regression>`_: |Build Status QuantileRegL1|

.. math::
    \min_{w} \frac{1}{n} \sum_{i=1}^{n} PB_q(y_i - X_i w) + \lambda ||w||_1.

where :math:`PB_q` is the pinball loss:

.. math::
    PB_q(t) = q \max(t, 0) + (1 - q) \max(-t, 0) =
    \begin{cases}
        q t, & t > 0, \\
        0,    & t = 0, \\
        (1-q) t, & t < 0
    \end{cases}

- `Linear ICA <https://github.com/benchopt/benchmark_linear_ica>`_: |Build Status LinearICA|

Given some data :math:`X  \in \mathbb{R}^{d \times n}` assumed to be linearly
related to unknown independent sources :math:`S  \in \mathbb{R}^{d \times n}` with

.. math::
    X = A S

where :math:`A  \in \mathbb{R}^{d \times d}` is also unknown, the objective of
linear ICA is to recover :math:`A` up to permutation and scaling of its columns.
The objective in this benchmark is related to some estimation on :math:`A`
quantified with the so-called AMARI distance.

- `Approximate Joint Diagonalization (AJD) <https://github.com/benchopt/benchmark_jointdiag>`_: |Build Status JointDiag|

Given n square symmetric positive matrices :math:`C^i`, it consists of solving
the following problem:

.. math::
    \min_B \frac{1}{2n} \sum_{i=1}^n \log |\textrm{diag} (B C^i B^{\top}) | - \log | B C^i B^{\top} |

where :math:`|\cdot|` stands for the matrix determinant and :math:`\textrm{diag}` stands
for the operator that keeps only the diagonal elements of a matrix. Optionally, the
matrix :math:`B` can be enforced to be orthogonal.

See `benchmark_* repositories on GitHub <https://github.com/benchopt/>`_ for more.

Benchmark results
-----------------

All the public benchmark results are available at `Benchopt Benchmarks results <https://benchopt.github.io/results/>`_.

**Publish results**: You can directly publish the result of a run of ``benchopt`` on `Benchopt Benchmarks results <https://benchopt.github.io/results/>`_. You can have a look at this page to :ref:`publish_doc`.

.. include:: contrib.rst


Citing Benchopt
---------------

If you use ``Benchopt`` in a scientific publication, please cite the following paper

.. code-block:: bibtex

   @article{benchopt,
      author = {Moreau, Thomas and Massias, Mathurin and Gramfort, Alexandre and Ablin, Pierre 
                and Bannier, Pierre-Antoine and Charlier, Benjamin and Dagréou, Mathieu and Dupré la Tour, Tom 
                and Durif, Ghislain and F. Dantas, Cassio and Klopfenstein, Quentin 
                and Larsson, Johan and Lai, En and Lefort, Tanguy and Malézieux, Benoit 
                and Moufad, Badr and T. Nguyen, Binh and Rakotomamonjy, Alain and Ramzi, Zaccharie 
                and Salmon, Joseph and Vaiter, Samuel},
      title  = {Benchopt: Reproducible, efficient and collaborative optimization benchmarks},
      year   = {2022},
      url    = {https://arxiv.org/abs/2206.13424}
   }


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

.. |Build Status OLS| image:: https://github.com/benchopt/benchmark_ols/workflows/Tests/badge.svg
   :target: https://github.com/benchopt/benchmark_ols/actions
.. |Build Status NNLS| image:: https://github.com/benchopt/benchmark_nnls/workflows/Tests/badge.svg
   :target: https://github.com/benchopt/benchmark_nnls/actions
.. |Build Status Lasso| image:: https://github.com/benchopt/benchmark_lasso/workflows/Tests/badge.svg
   :target: https://github.com/benchopt/benchmark_lasso/actions
.. |Build Status LogRegL2| image:: https://github.com/benchopt/benchmark_logreg_l2/workflows/Tests/badge.svg
   :target: https://github.com/benchopt/benchmark_logreg_l2/actions
.. |Build Status LogRegL1| image:: https://github.com/benchopt/benchmark_logreg_l1/workflows/Tests/badge.svg
   :target: https://github.com/benchopt/benchmark_logreg_l1/actions
.. |Build Status HuberL2| image:: https://github.com/benchopt/benchmark_huber_l2/workflows/Tests/badge.svg
   :target: https://github.com/benchopt/benchmark_huber_l2/actions
.. |Build Status QuantileRegL1| image:: https://github.com/benchopt/benchmark_quantile_regression/workflows/Tests/badge.svg
   :target: https://github.com/benchopt/benchmark_quantile_regression/actions
.. |Build Status LinearSVM| image:: https://github.com/benchopt/benchmark_linear_svm_binary_classif_no_intercept/workflows/Tests/badge.svg
   :target: https://github.com/benchopt/benchmark_linear_svm_binary_classif_no_intercept/actions
.. |Build Status LinearICA| image:: https://github.com/benchopt/benchmark_linear_ica/workflows/Tests/badge.svg
   :target: https://github.com/benchopt/benchmark_linear_ica/actions
.. |Build Status JointDiag| image:: https://github.com/benchopt/benchmark_jointdiag/workflows/Tests/badge.svg
   :target: https://github.com/benchopt/benchmark_jointdiag/actions
