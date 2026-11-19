Frequently asked questions (FAQ)
--------------------------------

.. dropdown:: Is benchopt only for optimization? (No!)

    No! Despite its name, Benchopt supports both **machine learning**, **optimization** and **infrastructure** benchmarks.
    Most features in benchopt are common to both types of benchmarks.
    The main difference lies in how performance is evaluated:

    - **Optimization benchmarks**: Track iterative solvers' convergence
      over time and iterations.
    - **ML benchmarks**: Compare estimators/models on prediction tasks
      (accuracy, F1, etc.).

    Use our `ML template <https://github.com/benchopt/template_benchmark_ml>`_
    to get started quickly.

.. dropdown:: Is benchopt restricted to a fixed set of benchmarks?

    No! Benchopt is a **framework** to write and run benchmarks, not a fixed
    set of benchmarks. You can create your own benchmark by writing a few lines
    of code, and share it with the community.
    See :ref:`write_benchmark` for a complete guide on how to write a benchmark.

.. dropdown:: Can I run a benchmark in parallel and use a cache?

    Benchopt allows to run different benchmarked methods in parallel, either with ``joblib`` using ``-j 4`` to run on multiple CPUs of a single machine or with more advanced distributed backend, detailed in :ref:`parallel_run`.

    Moreover, benchopt caches results natively to avoid wasteful recomputation. The cache is automatically invalidated when the code of a solver, dataset, or objective changes. You can also bypass the cache with ``--no-cache`` to force re-running all combinations.


.. dropdown:: How can I write a benchmark?

    Learn how to :ref:`write_benchmark`, including creating an objective, a solver, and a dataset.

    Also take a look at our template repository for `Optimization <https://github.com/benchopt/template_benchmark>`_ and `ML <https://github.com/benchopt/template_benchmark_ml>`_ to easily start a new benchmark.


.. dropdown:: How can I reuse code in a benchmark?

    For some solvers and datasets, it is handy to share some operations or pre-processing steps.
    Benchopt allows to factorize this code by :ref:`benchmark_utils_import`.
