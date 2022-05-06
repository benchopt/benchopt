Benchmark repository for optimization
=====================================

|Test Status| |Python 3.6+| |codecov|

BenchOpt is a benchmarking suite for optimization algorithms.
It is built for simplicity, transparency, and reproducibility.

Benchopt is implemented in Python, and can run algorithms
written in **many programming languages**
(`example <https://benchopt.github.io/auto_examples/plot_run_benchmark_python_R.html>`_).
So far, Benchopt has been tested with `Python <https://www.python.org/>`_,
`R <https://www.r-project.org/>`_, `Julia <https://julialang.org/>`_
and `C/C++ <https://isocpp.org/>`_ (compiled binaries with a command line interface).
Programs available via
`conda <https://docs.conda.io/en/latest/>`_ should be compatible.

BenchOpt is run through a command line interface as described
in the `API Documentation <https://benchopt.github.io/api.html>`_.
Replicating an optimization benchmark should
be **as simple as doing**:

.. code-block::

    conda create -n benchopt python
    conda activate benchopt
    pip install benchopt
    git clone https://github.com/benchopt/benchmark_logreg_l2
    benchopt install -e benchmark_logreg_l2 -s cd -s sklearn
    benchopt run -e ./benchmark_logreg_l2 -s cd -s sklearn

Running this command will give you a benchmark plot on l2-regularized
logistic regression:

.. figure:: https://benchopt.github.io/_images/sphx_glr_plot_run_benchmark_001.png
   :target: how.html
   :align: center
   :scale: 80%

See the `List of optimization problems available`_ below.

Learn how to `create a new benchmark <https://benchopt.github.io/how.html>`_
using the `benchmark template <https://github.com/benchopt/template_benchmark>`_.

Install
--------

The command line tool to run the benchmarks can be installed through `pip`. In order to allow `benchopt`
to automatically install solvers dependencies, the install needs to be done in a `conda` environment.


.. code-block::

    conda create -n benchopt python
    conda activate benchopt

To get the **latest release**, use:

.. code-block::

    pip install benchopt

To get the **latest development version**, use:

.. code-block::

    pip install -U -i https://test.pypi.org/simple/ benchopt

Then, existing benchmarks can be retrieved from git or created locally.
For instance, the benchmark for Lasso can be retrieved with:

.. code-block::

    git clone https://github.com/benchopt/benchmark_lasso


Command line usage
------------------

To run the Lasso benchmark on all datasets and with all solvers, run:

.. code-block::

    benchopt run --env ./benchmark_lasso

To get more details about the different options, run:

.. code-block::

    benchopt run -h

or read the `API Documentation <https://benchopt.github.io/api.html>`_.

List of optimization problems available
---------------------------------------

- `Ordinary Least Squares (OLS) <https://github.com/benchopt/benchmark_ols>`_ |Build Status OLS|
- `Non-Negative Least Squares (NNLS) <https://github.com/benchopt/benchmark_nnls>`_ |Build Status NNLS|
- `LASSO: L1-regularized least squares <https://github.com/benchopt/benchmark_lasso>`_ |Build Status Lasso|
- `L2-regularized logistic regression <https://github.com/benchopt/benchmark_logreg_l2>`_ |Build Status LogRegL2|
- `L1-regularized logistic regression <https://github.com/benchopt/benchmark_logreg_l1>`_ |Build Status LogRegL1|
- `L2-regularized Huber regression <https://github.com/benchopt/benchmark_huber_l2>`_ |Build Status HuberL2|
- `L1-regularized quantile regression <https://github.com/benchopt/benchmark_quantile_regression>`_ |Build Status QuantileRegL1|
- `Linear SVM for binary classification <https://github.com/benchopt/benchmark_linear_svm_binary_classif_no_intercept>`_ |Build Status LinearSVM|
- `Linear ICA <https://github.com/benchopt/benchmark_linear_ica>`_ |Build Status LinearICA|

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
