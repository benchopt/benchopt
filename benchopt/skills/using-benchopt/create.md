# Creating a benchopt benchmark

Guidance for authoring a *benchmark* (a repo of datasets/solvers/objective).
This file covers **benchmark-wide**
concerns; for individual components see [add-objective.md](./add-objective.md),
[add-solver.md](./add-solver.md), and [add-dataset.md](./add-dataset.md).

After each change, lint (`flake8 .` or `ruff check .`) and run a `benchopt run`
smoke test with a debug config (template:
[`assets/config_run.yml`](./assets/config_run.yml)), or a
`benchopt test . --skip-install` to catch early design failures.

## Start from a template

Clone/copy **`template_benchmark`** (or **`template_benchmark_ml`** for ML) from
`github.com/benchopt`. Do not hand-build the layout — the template ships the
correct `objective.py`, `datasets/`, `solvers/`, `benchmark_utils/`, the test
config wiring, and the CI workflows (see below).

## Component contract (overview)

Every class needs a `name` attribute. Data flows as dicts (`→`), except
`Solver.run()` which is only executed and carries no data (`|`):
`Dataset.get_data()` → `Objective.set_data()` → `Objective.get_objective()`
→ `Solver.set_objective()` | `Solver.run()` | `Solver.get_result()`
→ `Objective.evaluate_result()`.
`Solver.run()` (between `set_objective` and `get_result`) is the timed part.

## Key design choices

Before writing components, settle:

- **What constitutes a dataset** — just data (typical ML), data + model (more
  optimization-style), or data + hardware (more infra-style).
- **What is handed to the method vs. kept for evaluation only** — i.e. the split
  between what `get_objective()` exposes to solvers and what the objective keeps
  to score their results.
- **How to let methods compare fairly** — expose a generic payload so every
  solver sees the same inputs. See [add-objective.md](./add-objective.md) for the
  authoring detail (evaluate_result format, benchmark-wide defaults,
  key_to_monitor, test wiring).

## Config and dependencies (benchmark-wide)

- **`benchmark_utils/` is shared code that ships with the benchmark — no install
  needed.** benchopt loads it and makes it importable as
  `from benchmark_utils import …` from any component, and pickles it *by value*
  so it travels to remote/distributed workers automatically. Use it to share
  helpers and to design base classes that solvers/datasets/objective subclass
  (e.g. a common `Solver` base wrapping shared setup). It must contain an
  `__init__.py` to be a proper module.
- **Requirements are per component**, not per `benchmark_utils` submodule — each
  objective/dataset/solver declares exactly what it imports (install detection
  is covered in [add-solver.md](./add-solver.md) and [add-dataset.md](./add-dataset.md)).
  Organise `benchmark_utils` by **topic** (one module per concern), import the
  specific submodule from each class, and keep `benchmark_utils/__init__.py`
  **empty** so importing one topic doesn't load the others.
- For data/config locations use **`get_data_path("key")`**
  (`from benchopt.config import get_data_path`); it resolves under the
  benchmark's configurable data folder, so it travels with any checkout. Ship
  small default/test configs in the repo and `.gitignore` only *generated* data.
- **Avoid module-level constants or hard-coded paths** (e.g.
  `_PROJECT_ROOT = Path(__file__).parent.parent`): they assume one machine's
  layout and break distribution. Express configuration as benchopt
  **parameters** set from the run config, not a bespoke config file the
  benchmark reads itself.
- To wrap an external code, prefer an **installable package with an in-process
  Python API** declared as a pip requirement (`pip::name @ git+https://…`) over
  `subprocess`/CLI/file round-trips.

## Data preparation and testing

- Put expensive one-time data generation in `Dataset.prepare()` and load it in
  `get_data()` (details in [add-dataset.md](./add-dataset.md)). Benchmark-wide,
  precompute reusable, solver-independent references in `prepare()` (e.g. a
  ground-truth trajectory) so each evaluation only does the cheap solver-dependent work.
- Give datasets/solvers a `test_parameters` dict pointing at a tiny, fast
  configuration, and when possible, ship a zero-dependency `Simulated` dataset so
  the benchmark always has a no-install smoke test.

## Continuous integration

The template ships GitHub Actions under `.github/workflows/` — reuse them rather
than hand-writing CI. `main.yml` runs on push/PR to `main`, on tags, and monthly,
and calls two reusable workflows from `benchopt/template_benchmark`:

- **Lint** (`lint_benchmarks.yml`): runs `flake8 .` by default, or `ruff check .`
  (selectable via a workflow input).
- **Test** (`test_benchmarks.yml`): runs `benchopt test . --env-name bench_test_env -vl`,
  then again with `--skip-install`, on an Ubuntu/macOS
  matrix using a Miniforge/mamba conda env (Python 3.12 by default). It tests
  against both benchopt `@main` and the latest release, and checks the
  `min_benchopt_version` declared in `objective.py`. Heavy data dirs can be
  cached to avoid re-downloads, by providing the cache_dir input in the test.yml workflow.

## Validate

- `flake8 .` or `ruff check .` on the changed files.
- `benchopt run . -d Simulated -s <solver>` as a no-dependency smoke test.
- `benchopt test . -k <Dataset>` to exercise `test_parameters` (skip the
  `*_install` test if your env cannot build isolated envs).

## Doc links

- Benchmark structure & workflow: https://benchopt.github.io/stable/benchmark_workflow/index.html
- Class config (parameters, requirements, hooks): https://benchopt.github.io/stable/user_guide/class_customization.html
- Writing a benchmark: https://benchopt.github.io/stable/how.html
