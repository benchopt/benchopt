---
name: using-benchopt
description: >
  All things benchopt: running a benchmark, authoring components (solvers,
  datasets, objectives), creating a new benchmark repo, parallel and cluster
  execution, exploring and managing result files, debugging benchmark code,
  and the full CLI reference. Use whenever working on a benchopt benchmark or
  the benchopt library itself — including benchopt run, benchopt install,
  benchopt plot, benchopt merge, benchopt publish, benchopt test, benchopt prepare,
  add solver, add dataset, add objective, create benchmark,
  convergence curve, parquet results, outputs/, evaluate_result, key_to_monitor,
  get_data, set_data, get_objective, set_objective, get_result, get_one_result,
  stopping_criterion, NoCriterion, SufficientProgressCriterion,
  sampling_strategy, run_once, callback, iteration, diverged, diverging curve,
  curve stops early, fixed-budget training, stale cache, force-solver, no-cache,
  safe_import_context, pip requirements, conda channel requirements,
  test_parameters, test_config, Simulated dataset, template_benchmark,
  benchmark_utils, min_benchopt_version, running benchopt on SLURM,
  benchopt parallel config, benchopt dask, benchopt n-jobs.
---

# Benchopt

Benchopt is a benchmark framework for optimization algorithms. Benchmarks are
git repos containing an `objective.py`, a `datasets/` folder, and a `solvers/`
folder. Solvers are compared on convergence curves or fixed-budget metrics.

## Sub-files

Load the relevant sub-file for the task at hand:

- [**add-objective.md**](./add-objective.md) — implement or fix the `Objective` (evaluate_result, metrics, benchmark-wide defaults)
- [**add-solver.md**](./add-solver.md) — implement or fix a `Solver` class
- [**add-dataset.md**](./add-dataset.md) — implement or fix a `Dataset` class
- [**create.md**](./create.md) — author a new benchmark repo from scratch
- [**run.md**](./run.md) — run an existing benchmark, manage caching and config
- [**parallel.md**](./parallel.md) — scale to local cores or a SLURM cluster
- [**results.md**](./results.md) — explore, plot, merge, and publish results
- [**debug.md**](./debug.md) — drive benchmark code from Python without the CLI
- [**cli-reference.md**](./cli-reference.md) — all CLI subcommands at a glance

## Assets (copy-paste templates)

- [`assets/solver.py`](./assets/solver.py) — `BaseSolver` template
- [`assets/dataset.py`](./assets/dataset.py) — `BaseDataset` template with `Simulated`
- [`assets/objective.py`](./assets/objective.py) — `BaseObjective` template
- [`assets/config_run.yml`](./assets/config_run.yml) — run config file
- [`assets/config_parallel_slurm.yml`](./assets/config_parallel_slurm.yml) — SLURM parallel config
- [`assets/debug_snippet.py`](./assets/debug_snippet.py) — interactive debugging boilerplate

## Quick smoke test

```bash
benchopt run . -d Simulated -s <solver> -n 5   # fast no-install check
benchopt test . --skip-install                  # design-level test suite
```
