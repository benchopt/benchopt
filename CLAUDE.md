## Scratch space

Use `agent_space/` (git-ignored, at repo root) for temporary scripts, scratch files, and throwaway experiments. Do not commit files from this directory.

## Environment

If a tool you need (`pip`, `python`, `pytest`, `flake8`, `sphinx-build`, etc.) is missing, check for a `.venv` in the project root or its parent and activate it before retrying. If no `.venv` is found, stop and ask the user — do **not** install tools or look for alternatives.

## Common commands

- **Install (editable, with dev extras):** `pip install -e ".[test,doc]"`
- **Lint:** `flake8 .` (config in `pyproject.toml` / `setup.cfg`).
- **Run all tests:** `pytest` from the repo root.
- **Run a subset:** tests live next to the code (e.g. `benchopt/tests/`, `benchopt/cli/tests/`, `benchopt/plotting/tests/`, `benchopt/utils/tests/`). Pass the directory or file to avoid running everything: `pytest benchopt/plotting/tests/`. Single test: `pytest benchopt/tests/test_runner.py::test_name`.
- **Build docs:** `make html` from `doc/` (note: the directory is `doc/`, not `docs/`). Output lands in `doc/_build/html/`.
- **Clean stale benchmark conda envs:** `make clean-conda` (removes envs matching `benchopt_*`).
- **CLI entrypoint:** `benchopt` (defined in `[project.scripts]` → `benchopt.cli:benchopt`). Common subcommands: `benchopt run`, `benchopt install`, `benchopt plot`.

## Architecture

`benchopt` is a benchmarking framework that runs **solvers** against **datasets** for a given **objective**, in possibly isolated conda environments, and produces results + plots. The core abstractions live in `benchopt/`.

### Top-level package layout

- `base.py` — defines `BaseSolver`, `BaseDataset`, `BaseObjective`. These are the three classes a benchmark author subclasses. Solvers implement `set_objective` / `run` / `get_result`; the docstrings in `base.py` are the canonical contract.
- `benchmark.py` — `Benchmark` class that loads a benchmark folder (objective, datasets, solvers, config) by dynamically importing modules. Constants like `CACHE_DIR` (`__cache__`), `PACKAGE_NAME` (`benchmark_utils`), and `_RUNNING_BENCHMARK` (global handle to the active benchmark) live here.
- `runner.py` — orchestrates a benchmark run: seeding, repetitions, status handling (`FAILURE_STATUS` / `SUCCESS_STATUS`), dispatch through `parallel_run`, and saving results.
- `callback.py`, `stopping_criterion.py` — `_Callback`, `SingleRunCriterion`, `SufficientProgressCriterion`. Solvers using `sampling_strategy='callback'` are timed via the callback; others are driven by iteration/tolerance schedules.
- `cli/` — Click-based CLI. Three command groups assembled in `cli/__init__.py`: `main` (`run`, `install`), `helpers` (env / info), `process_results` (`plot`, `publish`, `generate-results`). Adding/changing a CLI flag means touching `cli/main.py` and the `_get_run_args` mapping.
- `plotting/` — result rendering. `default_plots.py` defines built-in plots, `generate_html.py` emits the static HTML report (templates in `plotting/html/`), `generate_matplotlib.py` produces static figures, `image_utils.py` handles image-typed objective outputs. `BasePlot` (re-exported from the top-level package) is the user extension point.
- `results/` — persistence & sharing. `parquet.py` is the on-disk format, `process.py` post-processes raw runs, `github.py` / `hugging_face.py` handle publication.
- `parallel_backends/` — pluggable executors: in-process / joblib, `dask_backend.py`, `slurm_executor.py` (submitit). `check_parallel_config` validates user config; `parallel_run` is the dispatch entry point used by the runner.
- `utils/` — most cross-cutting helpers. Notably:
  - `conda_env_cmd.py`, `shell_cmd.py` — drive `conda` / shell calls used to install solvers in isolated envs.
  - `dynamic_modules.py` — loads benchmark code from arbitrary paths.
  - `parametrized_name_mixin.py`, `seed_mixin.py`, `dependencies_mixin.py`, `class_property.py` — mixed into `BaseSolver` / `BaseDataset` to provide parameter expansion, deterministic seeding, and `requirements` handling.
  - `terminal_output.py`, `pdb_helpers.py`, `profiling.py`, `sys_info.py`, `temp_benchmark.py` — UX, debugging, and test scaffolding.
- `datasets/simulated.py` — the only first-party dataset (synthetic data); real datasets live in benchmark repos.
- `tests/` — package-level tests. `tests/fixtures.py` and `utils/temp_benchmark.py` build throwaway benchmarks on the fly; many tests rely on this rather than checked-in benchmark folders.

### Mental model for changes

- A benchmark is a *folder* (with `objective.py`, `solvers/`, `datasets/`, `plots/`), discovered dynamically — not a Python package installed alongside `benchopt`. When working on the runner, plotting, or CLI, prefer the temp-benchmark fixtures in `utils/temp_benchmark.py` over real benchmark repos.
- Solver / dataset isolation goes through conda. Anything that touches `requirements`, install flow, or env detection ends up in `utils/conda_env_cmd.py` + `utils/shell_cmd.py`. Tests that exercise this path are slow and may be skipped unless `conda` is available.
- Results flow: `runner.run_benchmark` → `parallel_backends.parallel_run` → per-`(objective, dataset, solver, repetition)` execution → `results.save_results` (parquet) → `plotting` consumes the parquet to render HTML / matplotlib.

## Documentation

Docs are Sphinx-based under `doc/`. Update them when changing user-facing behavior, then build with `make html` from `doc/` to confirm there are no warnings/errors. Examples under `doc/auto_examples/` are generated by `sphinx_gallery` from scripts the user runs separately — don't hand-edit them.
