Benchmark repository for optimization
=====================================

|Build Status| |Python 3.6+| |codecov|

BenchOpt is a package to simplify, make more transparent and
more reproducible the comparisons of optimization algorithms.

BenchOpt is written in Python but it is available with
`many programming languages <https://benchopt.github.io/auto_examples/plot_run_benchmark_python_R_julia.html>`_.
So far it has been tested with `Python <https://www.python.org/>`_,
`R <https://www.r-project.org/>`_, `Julia <https://julialang.org/>`_
and compiled binaries written in C/C++ available via a terminal
command. If it can be installed via
`conda <https://docs.conda.io/en/latest/>`_ it should just work!

BenchOpt is used through a command line as documented
in `api_documentation <https://benchopt.github.io/api.html>`_.
Ultimately running and replicating an optimization benchmark should
be **as simple as doing**:

.. code-block::

    $ benchopt run benchmarks/logreg_l2

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

This package can be installed through `pip` using:

.. code-block::

    $ pip install benchopt

Command line usage
------------------

To run Lasso benchmarks on all datasets and with all solvers, run:

.. code-block::

    $ benchopt run benchmarks/lasso

Use

.. code-block::

    $ benchopt run -h

for more details about different options or read the
`API Documentation <https://benchopt.github.io/api.html>`_.


.. |Build Status| image:: https://dev.azure.com/benchopt/benchopt/_apis/build/status/benchopt.benchOpt?branchName=master
   :target: https://dev.azure.com/benchopt/benchopt/_build/latest?definitionId=1&branchName=master
.. |Python 3.6+| image:: https://img.shields.io/badge/python-3.6%2B-blue
   :target: https://www.python.org/downloads/release/python-360/
.. |codecov| image:: https://codecov.io/gh/benchopt/benchOpt/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/benchopt/benchOpt
