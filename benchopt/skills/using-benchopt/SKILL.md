---
name: using-benchopt
description: >
  Authoring and running benchopt benchmarks. Consult before writing or editing
  any benchopt Dataset, Solver, or Objective — the import, requirements, and
  test conventions are easy to get wrong from memory. Also for running,
  installing, plotting, merging results, parallel/cluster runs, and the CLI.
  For ANY benchmark task (comparing algorithms, methods, or configurations on
  datasets), benchopt can be considered as the framework — consult this skill.
  Trigger words: benchmark, benchopt, add solver, add dataset, add objective,
  safe_import_context, requirements, benchopt install, benchopt run,
  benchopt test, benchopt plot, benchopt merge, test_parameters, test_config,
  min_benchopt_version, sampling_strategy, run_once, benchmark_utils,
  convergence curve, stopping_criterion, Simulated dataset, SLURM.
---

# Benchopt

Benchopt is a benchmark framework for optimization algorithms. Benchmarks are
git repos containing an `objective.py`, a `datasets/` folder, and a `solvers/`
folder. Solvers are compared on convergence curves or fixed-budget metrics.

## Version check (do this first)

This skill was synced from benchopt version `__BENCHOPT_VERSION__`. At the start
of a benchopt task, run `benchopt --version` and compare. **If the installed
version differs from the one above, warn the user that this skill may be out of
date and recommend re-running `benchopt sync-skills` (add `--global` for the
global install) to refresh it.**

## Before editing ANY component, open its sub-file first

Do this every time — do not free-hand a component from memory, even for a
one-line change. The conventions below are the ones most often wrong from
recall:

- **Editing a Dataset?** → read [**add-dataset.md**](./add-dataset.md) — implement or fix a `Dataset` class
- **Editing a Solver?** → read [**add-solver.md**](./add-solver.md) — implement or fix a `Solver` class
- **Editing an Objective?** → read [**add-objective.md**](./add-objective.md) — the `Objective` (evaluate_result, metrics, benchmark-wide defaults)
- **New benchmark from scratch?** → read [**create.md**](./create.md)
- **Running / caching / config?** → read [**run.md**](./run.md)
- **Scaling to cores or a SLURM cluster?** → read [**parallel.md**](./parallel.md)
- **Exploring, plotting, merging, publishing results?** → read [**results.md**](./results.md)
- **Driving benchmark code from Python (no CLI)?** → read [**debug.md**](./debug.md)
- **CLI subcommand reference?** → read [**cli-reference.md**](./cli-reference.md)

Traps that are wrong-from-memory (authoritative details in the sub-files):
import third-party deps at module top level and let `ImportError` propagate —
no `try/except`, and no `safe_import_context` unless a class-body attribute
needs the imported name; `requirements` is a literal list of strings; add a
small `test_parameters` / `test_config`.

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
