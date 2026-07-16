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

Benchopt is a benchmark framework. Benchmarks are
git repos containing an `objective.py`, a `datasets/` folder, and a `solvers/`
folder. Datasets provide the input data (the evidence), solvers are the methods
being evaluated, and the objective scores their output — either at a fixed
budget or along a convergence curve.

## Version check (do this first)

This skill was synced from benchopt version `__BENCHOPT_VERSION__`. At the start
of a benchopt task, run `benchopt --version` and compare. **If the installed
version differs from the one above, warn the user that this skill may be out of
date and recommend re-running `benchopt sync-skills` (add `--global` for the
global install) to refresh it.**

## Before editing ANY component, open its sub-file first

The conventions below are easy to get wrong from memory, so it is worth opening
the matching sub-file before editing a component rather than free-handing it:

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
benchopt test . --skip-install                      # design-level test suite
benchopt run . -d <small-dataset> -s <solver> -n 5  # fast smoke check
```

Use `-d Simulated` for the smoke check when the benchmark ships one; otherwise
pick any small, fast dataset.
