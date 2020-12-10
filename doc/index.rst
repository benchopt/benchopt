Benchmark repository for optimization
=====================================

|Build Status| |Python 3.6+| |codecov|

BenchOpt is a package to simplify, make more transparent and
more reproducible the comparisons of optimization algorithms.

BenchOpt is written in Python but it is available with
`many programming languages <auto_examples/plot_run_benchmark_python_R_julia.html>`_.
So far it has been tested with `Python <https://www.python.org/>`_,
`R <https://www.r-project.org/>`_, `Julia <https://julialang.org/>`_
and compiled binaries written in C/C++ available via a terminal
command. If it can be installed via
`conda <https://docs.conda.io/en/latest/>`_ it should just work!

BenchOpt is used through a command line as documented
in :ref:`cli_documentation`. Ultimately running and replicating an
optimization benchmark should be **as simple as doing**:

.. code-block::

    $ git clone https://github.com/benchopt/benchmark_logreg_l2
    $ benchopt run ./benchmark_logreg_l2

Running these commands will fetch the benchmark files and give you a benchmark plot on l2-regularized logistic regression:

.. figure:: auto_examples/images/sphx_glr_plot_run_benchmark_001.png
   :target: how.html
   :align: center
   :scale: 80%

Learn how to :ref:`how`.

Install
--------

This package can be installed through `pip` using:

.. code-block::

    $ pip install benchopt

This will install the command line tool to run the benchmark. Then, existing
benchmarks can be retrieved from git or created locally. To discover which
benchmarks are presently available look for
`benchmark_* repositories on GitHub <https://github.com/benchopt/>`_,
such as for `l1-regularized logistic regression <https://github.com/benchopt/benchmark_logreg_l1>`_.
This benchmark can then be retrieved locally with:

.. code-block::

    $ git clone https://github.com/benchopt/benchmark_lasso.git

Command line usage
------------------

To run Lasso benchmarks on all datasets and with all solvers, run:

.. code-block::

    $ benchopt run benchmark_lasso

Use

.. code-block::

    $ benchopt run -h

for more details about different options read the :ref:`api_documentation`.

List of optimization problems available
---------------------------------------

Notation:  In what follows, n (or n_samples) stands for the number of samples and p (or n_features) stands for the number of features.

.. math::

 y \in \mathbb{R}^n, X = [x_1^\top, \dots, x_n^\top]^\top \in \mathbb{R}^{n \times p}

- `ols`_: ordinary least-squares. This consists in solving the following program:

.. math::

    \min_w \frac{1}{2} \|y - Xw\|^2_2

- `nnls`_: non-negative least-squares. This consists in solving the following program:

.. math::

    \min_{w \geq 0} \frac{1}{2} \|y - Xw\|^2_2

- `lasso`_: l1-regularized least-squares. This consists in solving the following program:

.. math::

    \min_w \frac{1}{2} \|y - Xw\|^2_2 + \lambda \|w\|_1

- `logreg_l2`_: l2-regularized logistic regression. This consists in solving the following program:

.. math::

    \min_w \sum_i \log(1 + \exp(-y_i x_i^\top w)) + \frac{\lambda}{2} \|w\|_2^2

- `logreg_l1`_: l1-regularized logistic regression. This consists in solving the following program:

.. math::

    \min_w \sum_i \log(1 + \exp(-y_i x_i^\top w)) + \lambda \|w\|_1


Contents
========

.. toctree::
   :maxdepth: 1

   cli
   api
   how
   Fork benchopt on Github <https://github.com/benchopt/benchopt>

.. |Build Status| image:: https://dev.azure.com/benchopt/benchopt/_apis/build/status/benchopt.benchOpt?branchName=master
   :target: https://dev.azure.com/benchopt/benchopt/_build/latest?definitionId=1&branchName=master
.. |Python 3.6+| image:: https://img.shields.io/badge/python-3.6%2B-blue
   :target: https://www.python.org/downloads/release/python-360/
.. |codecov| image:: https://codecov.io/gh/benchopt/benchOpt/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/benchopt/benchOpt

.. _`ols`: https://github.com/benchopt/benchmark_ols
.. _`nnls`: https://github.com/benchopt/benchmark_nnls
.. _`lasso`: https://github.com/benchopt/benchmark_lasso
.. _`logreg_l1`: https://github.com/benchopt/benchmark_logreg_l1
.. _`logreg_l2`: https://github.com/benchopt/benchmark_logreg_l2
