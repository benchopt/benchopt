Benchmark repository for optimization
=====================================

|Test Status| |Python 3.6+| |codecov|

BenchOpt is a package to simplify, make more transparent and
more reproducible the comparisons of optimization algorithms.

BenchOpt is written in Python but it is available with
`many programming languages <https://benchopt.github.io/auto_examples/plot_run_benchmark_python_R_julia.html>`_.
So far it has been tested with `Python <https://www.python.org/>`_,
`R <https://www.r-project.org/>`_, `Julia <https://julialang.org/>`_
and compiled binaries written in C/C++ available via a terminal
command. If it can be installed via
`conda <https://docs.conda.io/en/latest/>`_ it should just work!

BenchOpt is used through a command line as described
in `the API Documentation <https://benchopt.github.io/api.html>`_.
Ultimately running and replicating an optimization benchmark should
be **as simple as doing**:

.. code-block::

    $ git clone https://github.com/benchopt/benchmark_logreg_l2
    $ benchopt run --env ./benchmark_logreg_l2

Running this command will give you a benchmark plot on l2-regularized
logistic regression:

.. figure:: https://benchopt.github.io/_images/sphx_glr_plot_run_benchmark_001.png
   :target: how.html
   :align: center
   :scale: 80%

To discover which benchmarks are presently available look
for `benchmark_* repositories on GitHub <https://github.com/benchopt/>`_,
such as for
`l1-regularized logistic regression <https://github.com/benchopt/benchmark_logreg_l1>`_.


Learn how to `write a benchmark on our documentation <https://benchopt.github.io/how.html>`_.

Install
--------

This package can be installed through `pip`. To get the **last release**, use:

.. code-block::

    $ pip install benchopt

And to get the **latest development version**, you can use:

.. code-block::

    $ pip install -U https://github.com/benchopt/benchOpt/archive/master.zip

This will install the command line tool to run the benchmark. Then, existing
benchmarks can be retrieved from git or created locally. For instance, the
benchmark for Lasso can be retrieved with:

.. code-block::

    $ git clone https://github.com/benchopt/benchmark_lasso


Command line usage
------------------

To run the Lasso benchmark on all datasets and with all solvers, run:

.. code-block::

    $ benchopt run --env ./benchmark_lasso

Use

.. code-block::

    $ benchopt run -h

to get more details about the different options or read the
`API Documentation <https://benchopt.github.io/api.html>`_.


List of optimization problems available
---------------------------------------

- `ols`_: ordinary least-squares.
- `nnls`_: non-negative least-squares.
- `lasso`_: l1-regularized least-squares.
- `logreg_l2`_: l2-regularized logistic regression.
- `logreg_l1`_: l1-regularized logistic regression.

[![test]()]()

.. |Test Status| image:: https://github.com/benchopt/benchOpt/actions/workflows/test.yml/badge.svg
   :target: https://github.com/benchopt/benchOpt/actions/workflows/test.yml
.. |Python 3.6+| image:: https://img.shields.io/badge/python-3.6%2B-blue
   :target: https://www.python.org/downloads/release/python-360/
.. |codecov| image:: https://codecov.io/gh/benchopt/benchOpt/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/benchopt/benchOpt

.. _`ols`: https://github.com/benchopt/benchmark_ols
.. _`nnls`: https://github.com/benchopt/benchmark_nnls
.. _`lasso`: https://github.com/benchopt/benchmark_lasso
.. _`logreg_l1`: https://github.com/benchopt/benchmark_logreg_l1
.. _`logreg_l2`: https://github.com/benchopt/benchmark_logreg_l2
