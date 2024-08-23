.. image:: https://raw.githubusercontent.com/benchopt/communication_materials/main/posters/images/logo_benchopt.png
   :width: 350
   :align: center

*—Making your ML and optimization benchmarks simple and open—*

----

|Test Status| |codecov| |Documentation| |Python 3.6+| |install-per-months| |discord| |SWH|

``Benchopt`` is a benchmarking suite tailored for machine learning workflows.
It is built for simplicity, transparency, and reproducibility.
It is implemented in Python but can run algorithms written in **many programming languages**.


So far, ``benchopt`` has been tested with `Python <https://www.python.org/>`_,
`R <https://www.r-project.org/>`_, `Julia <https://julialang.org/>`_
and `C/C++ <https://isocpp.org/>`_ (compiled binaries with a command line interface).
Programs available via `conda <https://docs.conda.io/en/latest/>`_ should be compatible as well.
See for instance an `example of usage <https://benchopt.github.io/auto_examples/plot_run_benchmark_python_R.html>`_ with ``R``.


Install
-------

It is recommended to use ``benchopt`` within a ``conda`` environment to fully-benefit
from ``benchopt`` Command Line Interface (CLI).


To install ``benchopt``, start by creating a new ``conda`` environment and then activate it

.. code-block:: bash

    conda create -n benchopt python
    conda activate benchopt

Then run the following command to install the **latest release** of ``benchopt``

.. code-block:: bash

    pip install -U benchopt

It is also possible to use the **latest development version**. To do so, run instead

.. code-block:: bash

    pip install git+https://github.com/benchopt/benchopt.git


Getting started
---------------

After installing ``benchopt``, you can

- replicate/modify an existing benchmark
- create your own benchmark


Using an existing benchmark
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Replicating an existing benchmark is simple.
Here is how to do so for the `L2-logistic Regression benchmark <https://github.com/benchopt/benchmark_logreg_l2>`_.

1. Clone the benchmark repository and ``cd`` to it

.. code-block:: bash

   git clone https://github.com/benchopt/benchmark_logreg_l2
   cd benchmark_logreg_l2

2. Install the desired solvers automatically with ``benchopt``

.. code-block:: bash

   benchopt install . -s lightning -s sklearn

3. Run the benchmark to get the figure below

.. code-block:: bash

   benchopt run . --config ./example_config.yml


.. figure:: https://benchopt.github.io/_images/sphx_glr_plot_run_benchmark_001.png
   :target: how.html
   :align: center
   :width: 60%

These steps illustrate how to reproduce the `L2-logistic Regression benchmark <https://github.com/benchopt/benchmark_logreg_l2>`_.
Find the complete list of the `Available benchmarks`_.
Also, refer to the `documentation <https://benchopt.github.io/>`_ to learn more about ``benchopt`` CLI and its features.
You can also easily extend this benchmark by adding a dataset, solver or metric.
Learn that and more in the `Benchmark workflow <https://benchopt.github.io/benchmark_workflow/index.html>`_.


Creating a benchmark
^^^^^^^^^^^^^^^^^^^^

The section `Write a benchmark <https://benchopt.github.io/benchmark_workflow/write_benchmark.html>`_ of the documentation provides a tutorial
for creating a benchmark. The ``benchopt`` community also maintains
a `template benchmark <https://github.com/benchopt/template_benchmark>`_ to quickly and easily start a new benchmark.


Finding help
------------

Join ``benchopt`` `discord server <https://discord.gg/EA2HGQb7nv>`_ and get in touch with the community!
Feel free to drop us a message to get help with running/constructing benchmarks
or (why not) discuss new features to be added and future development directions that ``benchopt`` should take.


Citing Benchopt
---------------

``Benchopt`` is a continuous effort to make reproducible and transparent ML and optimization benchmarks.
Join us in this endeavor! If you use ``benchopt`` in a scientific publication, please cite

.. code-block:: bibtex

   @inproceedings{benchopt,
      author    = {Moreau, Thomas and Massias, Mathurin and Gramfort, Alexandre
                   and Ablin, Pierre and Bannier, Pierre-Antoine
                   and Charlier, Benjamin and Dagréou, Mathieu and Dupré la Tour, Tom
                   and Durif, Ghislain and F. Dantas, Cassio and Klopfenstein, Quentin
                   and Larsson, Johan and Lai, En and Lefort, Tanguy
                   and Malézieux, Benoit and Moufad, Badr and T. Nguyen, Binh and Rakotomamonjy,
                   Alain and Ramzi, Zaccharie and Salmon, Joseph and Vaiter, Samuel},
      title     = {Benchopt: Reproducible, efficient and collaborative optimization benchmarks},
      year      = {2022},
      booktitle = {NeurIPS},
      url       = {https://arxiv.org/abs/2206.13424}
   }


Available benchmarks
--------------------

.. list-table::
   :widths: 70 15 15
   :header-rows: 1

   * - Problem
     - Results
     - Build Status
   * - `Ordinary Least Squares (OLS) <https://github.com/benchopt/benchmark_ols>`_
     - `Results <https://benchopt.github.io/results/benchmark_ols.html>`__
     - |Build Status OLS|
   * - `Non-Negative Least Squares (NNLS) <https://github.com/benchopt/benchmark_nnls>`_
     - `Results <https://benchopt.github.io/results/benchmark_nnls.html>`__
     - |Build Status NNLS|
   * - `LASSO: L1-Regularized Least Squares <https://github.com/benchopt/benchmark_lasso>`_
     - `Results <https://benchopt.github.io/results/benchmark_lasso.html>`__
     - |Build Status Lasso|
   * - `LASSO Path <https://github.com/jolars/benchmark_lasso_path>`_
     - `Results <https://benchopt.github.io/results/benchmark_lasso_path.html>`__
     - |Build Status Lasso Path|
   * - `Elastic Net <https://github.com/benchopt/benchmark_elastic_net>`_
     -
     - |Build Status ElasticNet|
   * - `MCP <https://github.com/benchopt/benchmark_mcp>`_
     - `Results <https://benchopt.github.io/results/benchmark_mcp.html>`__
     - |Build Status MCP|
   * - `L2-Regularized Logistic Regression <https://github.com/benchopt/benchmark_logreg_l2>`_
     - `Results <https://benchopt.github.io/results/benchmark_logreg_l2.html>`__
     - |Build Status LogRegL2|
   * - `L1-Regularized Logistic Regression <https://github.com/benchopt/benchmark_logreg_l1>`_
     - `Results <https://benchopt.github.io/results/benchmark_logreg_l1.html>`__
     - |Build Status LogRegL1|
   * - `L2-regularized Huber regression <https://github.com/benchopt/benchmark_huber_l2>`_
     -
     - |Build Status HuberL2|
   * - `L1-Regularized Quantile Regression <https://github.com/benchopt/benchmark_quantile_regression>`_
     - `Results <https://benchopt.github.io/results/benchmark_quantile_regression.html>`__
     - |Build Status QuantileRegL1|
   * - `Linear SVM for Binary Classification <https://github.com/benchopt/benchmark_linear_svm_binary_classif_no_intercept>`_
     -
     - |Build Status LinearSVM|
   * - `Linear ICA <https://github.com/benchopt/benchmark_linear_ica>`_
     -
     - |Build Status LinearICA|
   * - `Approximate Joint Diagonalization (AJD) <https://github.com/benchopt/benchmark_jointdiag>`_
     -
     - |Build Status JointDiag|
   * - `1D Total Variation Denoising <https://github.com/benchopt/benchmark_tv_1d>`_
     -
     - |Build Status TV1D|
   * - `2D Total Variation Denoising <https://github.com/benchopt/benchmark_tv_2d>`_
     -
     - |Build Status TV2D|
   * - `ResNet Classification <https://github.com/benchopt/benchmark_resnet_classif>`_
     - `Results <https://benchopt.github.io/results/benchmark_resnet_classif.html>`__
     - |Build Status ResNetClassif|
   * - `Bilevel Optimization <https://github.com/benchopt/benchmark_bilevel>`_
     - `Results <https://benchopt.github.io/results/benchmark_bilevel.html>`__
     - |Build Status Bilevel|




.. |Test Status| image:: https://github.com/benchopt/benchopt/actions/workflows/test.yml/badge.svg
   :target: https://github.com/benchopt/benchopt/actions/workflows/test.yml
.. |Python 3.6+| image:: https://img.shields.io/badge/python-3.6%2B-blue
   :target: https://www.python.org/downloads/release/python-360/
.. |Documentation| image:: https://img.shields.io/badge/documentation-latest-blue
   :target: https://benchopt.github.io
.. |codecov| image:: https://codecov.io/gh/benchopt/benchopt/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/benchopt/benchopt
.. |SWH| image:: https://archive.softwareheritage.org/badge/origin/https://github.com/benchopt/benchopt/
    :target: https://archive.softwareheritage.org/browse/origin/?origin_url=https://github.com/benchopt/benchopt
.. |discord| image:: https://dcbadge.vercel.app/api/server/EA2HGQb7nv?style=flat
   :target: https://discord.gg/EA2HGQb7nv
.. |install-per-months| image:: https://static.pepy.tech/badge/benchopt/month
   :target: https://pepy.tech/project/benchopt

.. |Build Status OLS| image:: https://github.com/benchopt/benchmark_ols/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_ols/actions
.. |Build Status NNLS| image:: https://github.com/benchopt/benchmark_nnls/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_nnls/actions
.. |Build Status Lasso| image:: https://github.com/benchopt/benchmark_lasso/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_lasso/actions
.. |Build Status Lasso Path| image:: https://github.com/jolars/benchmark_lasso_path/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_lasso_path/actions
.. |Build Status ElasticNet| image:: https://github.com/benchopt/benchmark_elastic_net/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_elastic_net/actions
.. |Build Status MCP| image:: https://github.com/benchopt/benchmark_mcp/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_mcp/actions
.. |Build Status LogRegL2| image:: https://github.com/benchopt/benchmark_logreg_l2/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_logreg_l2/actions
.. |Build Status LogRegL1| image:: https://github.com/benchopt/benchmark_logreg_l1/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_logreg_l1/actions
.. |Build Status HuberL2| image:: https://github.com/benchopt/benchmark_huber_l2/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_huber_l2/actions
.. |Build Status QuantileRegL1| image:: https://github.com/benchopt/benchmark_quantile_regression/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_quantile_regression/actions
.. |Build Status LinearSVM| image:: https://github.com/benchopt/benchmark_linear_svm_binary_classif_no_intercept/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_linear_svm_binary_classif_no_intercept/actions
.. |Build Status LinearICA| image:: https://github.com/benchopt/benchmark_linear_ica/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_linear_ica/actions
.. |Build Status JointDiag| image:: https://github.com/benchopt/benchmark_jointdiag/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_jointdiag/actions
.. |Build Status TV1D| image:: https://github.com/benchopt/benchmark_tv_1d/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_tv_1d/actions
.. |Build Status TV2D| image:: https://github.com/benchopt/benchmark_tv_2d/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_tv_2d/actions
.. |Build Status ResNetClassif| image:: https://github.com/benchopt/benchmark_resnet_classif/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_resnet_classif/actions
.. |Build Status Bilevel| image:: https://github.com/benchopt/benchmark_bilevel/actions/workflows/main.yml/badge.svg
   :target: https://github.com/benchopt/benchmark_bilevel/actions
