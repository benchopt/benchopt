.. _faq:

Frequently asked questions (FAQ)
--------------------------------

.. dropdown:: Can I use benchopt for ML benchmarks (not just optimization)?

    Yes! Despite its name, Benchopt supports both **machine learning** and **optimization** benchmarks.
    Most features in benchopt are common to both types of benchmarks.
    The main difference lies in how performance is evaluated:

    - **Optimization benchmarks**: Track iterative solvers' convergence
      over time and iterations.
    - **ML benchmarks**: Compare estimators/models on prediction tasks
      (accuracy, F1, etc.).

    Setting ``sampling_strategy = "run_once"`` for a solver or for the full
    benchmark allows to only evaluate once to completion.
    See :ref:`ml_benchmark` for a complete guide, or use our
    `ML template <https://github.com/benchopt/template_benchmark_ml>`_ to get started quickly.

.. dropdown:: How to add my solver to an existing benchmark?

    Visit the :ref:`add_solver` tutorial for a step-by-step procedure to add a solver to an existing benchmark.


.. dropdown:: How can I write a benchmark?

    Learn how to :ref:`write_benchmark`, including creating an objective, a solver, and a dataset.

    Also take a look at our template repository for `Optimization <https://github.com/benchopt/template_benchmark>`_ and `ML <https://github.com/benchopt/template_benchmark_ml>`_ to easily start a new benchmark.


.. dropdown:: How are performance curves constructed and the solvers stopped?

    One of benchopt's goals is to evaluate the method's performance with
    respect to its computational budget.
    Benchopt allows several strategies to vary the computational budget, that
    can be set on a per solver basis.
    It is also possible to set various stopping criterions to decide when to
    stop growing the computational budget, to avoid wasting resources.
    Visit the :ref:`performance_curves` page for more details.


.. dropdown:: How can I reuse code in a benchmark?

    For some solvers and datasets, it is handy to share some operations or pre-processing steps.
    Benchopt allows to factorize this code by :ref:`benchmark_utils_import`.


.. dropdown:: Can I run a benchmark in parallel?

    Benchopt allows to run different benchmarked methods in parallel, either with ``joblib`` using ``-j 4`` to run on multiple CPUs of a single machine or with more advanced distributed backend, detailed in :ref:`parallel_run`.
