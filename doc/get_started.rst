.. _get_started:

Get started
===========

Installation
~~~~~~~~~~~~

    Benchopt can be installed directly with pip.

    .. prompt:: bash $

        pip install benchopt

    To gain access to certain features, in particular to install the requirements of community benchmarks, ``benchopt`` needs to be installed in a ``conda`` environment.

Run an existing benchmark
~~~~~~~~~~~~~~~~~~~~~~~~~

   When running a benchmark, benchopt automatically detects all solvers and datasets defined in the repository, with their grid of parameters, and runs all combinations. This produces a result file that can be visualized with the interactive dashboard.

   The core of benchopt is thus to provide a simple interface to the part of
   the benchmark that is duplicated across all benchmarks: the loop that runs all methods on all datasets! With extra features as a bonus: caching, parallelism, reproducibility, and more.

   To run an existing benchmark, clone the repository, install its
   requirements, and run it:

   .. prompt:: bash $

      git clone https://github.com/benchopt/template_benchmark_ml.git
      benchopt install template_benchmark_ml  # only works in conda env
      benchopt run template_benchmark_ml

   See :ref:`run_benchmark` for a full walkthrough including CLI options,
   configuration files, and caching.


Create your own benchmark
~~~~~~~~~~~~~~~~~~~~~~~~~

   A benchmark is a folder with three types of components, each a Python file:

   .. code-block:: none

      my_benchmark/
      ├── objective.py
      ├── datasets/
      │   └── my_dataset.py
      └── solvers/
          └── my_solver.py

    Each file defines a component of the benchmark, that are then automatically discovered and linked with benchopt:

   - :ref:`Dataset <datasets>` — loads or generates data.
   - :ref:`Objective <objective>` — defines what is measured;
     ``evaluate_result()`` computes your metrics (accuracy, loss, throughput,
     …).
   - :ref:`Solver <solvers>` — the method under evaluation, train a model or
     solve an optimization problem.

   This structure is intentionally general: creating a benchmark is mostly a
   matter of deciding which concept in your problem maps to which class — what
   counts as "data", what counts as "performance", and what counts as
   "a method". Benchopt then handles the rest, including running all
   combinations, aggregating results, and providing a dashboard to visualize
   them, with enhanced features to make your life easier!

   See :ref:`write_benchmark` for complete guide on how to write a benchmark,
   or use one of our templates to get started quickly:
   `ML benchmarks <https://github.com/benchopt/template_benchmark_ml>`_ |
   `Optimization benchmarks <https://github.com/benchopt/template_benchmark>`_.


Key features
~~~~~~~~~~~~

**Caching** — Each run is cached (via joblib) so that re-running
``benchopt run`` skips combinations whose results are already stored.
The cache is invalidated automatically when the solver, objective, or dataset
code changes. To force re-running specific solvers, pass
``-f SOLVER_NAME``; to disable caching entirely, pass ``--no-cache``.
See :ref:`run_caching`.

**Parallelism** — Solver/dataset combinations run sequentially by default.
Pass ``-j N`` to use N local workers, or ``--parallel-config slurm.yml`` to
dispatch jobs on a cluster (SLURM, Dask, …).
See :ref:`parallel_run`.

**Reproducibility** — Call ``self.get_seed()`` in any component to obtain a
deterministic integer seed that changes with the repetition index. Run with
``--n-rep N`` to get N independent repetitions with different seeds.
See :ref:`controlling_randomness`.

**Parametrization** — Set ``parameters = {"lr": [1e-3, 1e-2]}`` on any class
to sweep over values. Benchopt runs the full Cartesian product automatically
and labels each curve in the dashboard.
See :ref:`parametrized`.

**Result management** — Results are ``.parquet`` files stored in
``./outputs``. Use ``benchopt merge`` to combine runs from different machines
or users, ``benchopt publish`` to share on GitHub or Hugging Face.
See :ref:`manage_results`.

**Convergence tracking** — For iterative solvers, set
``sampling_strategy = "callback"`` (or ``"iteration"`` / ``"tolerance"``) to
record how the objective evolves with compute budget. Benchopt handles the
timing and stopping logic.
See :ref:`iterative_solvers`.
