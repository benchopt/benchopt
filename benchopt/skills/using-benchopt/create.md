# Creating a benchopt benchmark

Guidance for authoring a *benchmark* (a repo of datasets/solvers/objective),
not for working on the benchopt library. This file covers **benchmark-wide**
concerns; for an individual component see [add-solver.md](./add-solver.md) and
[add-dataset.md](./add-dataset.md), and for running/results [run.md](./run.md).

After each change, lint (`flake8 .` or `ruff check .`) and run a `benchopt run`
smoke test with a debug config, or a `benchopt test . --skip-install` to catch early
design failures.

## Start from a template

Clone/copy **`template_benchmark`** (or **`template_benchmark_ml`** for ML) from
`github.com/benchopt`. Do not hand-build the layout — the template ships the
correct `objective.py`, `datasets/`, `solvers/`, `benchmark_utils/`, the test
config wiring, and the CI workflows (see below).

## The objective/dataset/solver contract

Every class needs a `name` attribute. Data flows between components as dicts:

- `Dataset.get_data()` → dict → `Objective.set_data(**data)`.
- `Objective.get_objective()` → dict → `Solver.set_objective(**obj)`.
- `Solver.get_result()` → dict → `Objective.evaluate_result(**res)`.
- `evaluate_result` must return a dict with a scalar `value` key (the quantity
  benchopt minimises); add any extra metric keys you like.

The `Objective` also exposes optional methods worth wiring early:

- `get_one_result()`: a dummy result used by `benchopt test` to validate metric
  computation (validation skipped if absent).
- `save_final_results(**res)`: persist artefacts (models, arrays) as a `.pkl`
  alongside the parquet results.
- `skip(**data)`: skip incompatible dataset/objective combinations.

**Set benchmark-wide defaults on the `Objective`** so all solvers inherit them:
`sampling_strategy` (e.g. `"run_once"` for ML), `stopping_criterion`, and
`python_version` to pin the conda env's Python. **Seed all randomness with
`self.get_seed(use_repetition=True)`** so `--n-repetitions` gives reproducible,
distinct runs (a bare `self.get_seed()` returns the same seed every repetition).

Two design rules that keep a benchmark extensible:

- **Keep solvers dataset-agnostic.** Have the dataset expose a generic payload
  (e.g. `fields: dict[str, ndarray]`) plus *optional callables* (`moments_fn`,
  …); solvers operate on the payload by name, and the objective calls the
  callables only when present. One set of solvers then serves many datasets.
- **Use `Objective.parameters`** to parametrize *evaluation* itself (e.g. a
  number of restart steps), not just solvers/datasets.

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
- **No module-level constants or hard-coded paths** (e.g.
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

## Validate locally

- `flake8 .` or `ruff check .` on the changed files.
- `benchopt run . -d Simulated -s <solver>` as a no-dependency smoke test.
- `benchopt test . -k <Dataset>` to exercise `test_parameters` (skip the
  `*_install` test if your env cannot build isolated envs).
