.. _faq:

Frequently asked questions (FAQ)
--------------------------------

.. dropdown:: How can I write a benchmark?

    Learn how to :ref:`write_benchmark`, including creating an objective, a solver, and
    a dataset.


.. dropdown:: How performance curves are constructed?

    The goal of benchopt is to evaluate the evolution of a method's performance with respect to its computational budget.
    For evaluating this, benchopt allows to vary the computational budget for both black-box solvers and solvers that allow for callbacks.
    Learn :ref:`performance_curves`.
    Note that the budget varying strategy can also be configured on a per-solver basis, as described in: :ref:`sampling_strategy`.


.. dropdown:: How can I reuse code in a benchmark?

    For some solver and datasets, it is necessary to share some operations or pre-processing steps.
    Benchopt allows to factorize this code by :ref:`benchmark_utils_import`.


.. dropdown:: Can I run a benchmark in parallel?

    Benchopt allows to run different benchmarked methods in parallel, either with ``joblib`` using ``-j 4`` to run on multiple CPUs of a single machine or using SLURM, as described in :ref:`slurm_run`.
