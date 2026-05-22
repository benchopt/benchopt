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

   To run an existing benchmark, clone the repository, install its
   requirements, and run it:

   .. prompt:: bash $

      git clone https://github.com/benchopt/template_benchmark_ml.git
      benchopt install template_benchmark_ml  # only works in conda env
      benchopt run template_benchmark_ml

   This produces an interactive HTML dashboard with the results.

   See :ref:`run_benchmark` for a full walkthrough including CLI options,
   configuration files, and caching.


Create your own benchmark
~~~~~~~~~~~~~~~~~~~~~~~~~

   A benchopt benchmark has three ingredients:

   - ``Dataset``: specifies how to load data,
   - ``Objective``: defines the evaluation metrics,
   - ``Solver``: implements the method to evaluate.

   This same structure works for ML, optimization, or infrastructure benchmarks.
   See :ref:`write_benchmark` for complete examples and all available options.


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
