.. _faq:

Frequently asked questions (FAQ)
--------------------------------


.. dropdown:: How to add my solver to an existing benchmark?

    Visit the :ref:`add_solver` tutorial for a step-by-step procedure to add a solver to an existing benchmark.


.. dropdown:: How can I write a benchmark?

    Learn how to :ref:`write_benchmark`, including creating an objective, a solver, and a dataset.


.. dropdown:: How are performance curves constructed?

    The goal of benchopt is to evaluate the evolution of a method's performance with respect to its computational budget.
    For evaluating this, benchopt allows to vary the computational budget for both black-box solvers and solvers that allow for callbacks.
    Visit the :ref:`performance_curves` page for more detail.
    Note that the budget varying strategy can be configured on a per-solver basis, as described in: :ref:`sampling_strategy`.


.. dropdown:: How can I reuse code in a benchmark?

    For some solver and datasets, it is handy to share some operations or pre-processing steps.
    Benchopt allows to factorize this code by :ref:`benchmark_utils_import`.


.. dropdown:: Can I run a benchmark in parallel?

    Benchopt allows to run different benchmarked methods in parallel, either with ``joblib`` using ``-j 4`` to run on multiple CPUs of a single machine or using SLURM, as described in :ref:`slurm_run`.
