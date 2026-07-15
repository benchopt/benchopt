# benchopt Implementation Design Guidelines

## Design philosophy

benchopt exists to give benchmark authors **maximum flexibility with minimal
friction**, and to keep **benchmark definition separate from the plumbing**.
Weigh changes against these:

- **Definition vs plumbing.** Authors write only `objective.py`, `solvers/`,
  and `datasets/`, subclassing `BaseObjective` / `BaseSolver` / `BaseDataset`;
  they never touch execution. Keep the runner, caching, discovery, and CLI
  (`runner.py`, `benchmark.py`, `cli/`) out of the user-facing contract in
  `base.py`.
- **Keep base classes thin.** Cross-cutting plumbing is factored into mixins
  (`ParametrizedNameMixin`, `DependenciesMixin`, `SeedMixin`). New shared
  machinery usually belongs in a mixin or `utils/`, not inlined into a base
  class.
- **Minimize friction.** A working benchmark should need very little. Prefer
  sensible defaults and optional hooks over required boilerplate — `skip`
  defaults to False, `get_one_result` is optional, `_default_split` is used
  unless the author defines `split`, and `sampling_strategy` /
  `stopping_criterion` are inherited from the Objective when unset. When adding
  to the contract, ask whether it can have a default.
- **One API, many strategies.** Prefer an abstraction that lets a single API
  serve several use cases over special-casing. `sampling_strategy`
  (`iteration` / `callback` / `run_once`) lets one `Solver.run` cover iterative,
  callback-monitored, and fixed-budget training; the stopping criterion is
  derived from it.
- **Make alternatives pluggable backends, not conditionals.** Parallel execution
  (`parallel_backends/`: loky/dask/submitit) and install backends (conda/uv) are
  selected by name behind a stable interface. Extend by adding a backend, not by
  threading `if backend == ...` through the call sites.
- **Hand authors managed helpers for cross-cutting concerns.** Rather than making
  benchmarks reimplement plumbing, the base classes expose helpers that do it
  correctly: `get_data_path` (shared, configurable data location), `get_seed`
  (reproducible, cache-aware randomness scoped per component/repetition), and
  `get_run_output_path` (a unique dir for per-run artifacts). When a new concern
  cuts across benchmarks, prefer adding such a helper over documenting a recipe
  authors must copy.

## Validating changes

- **Always run `flake8` before declaring a change done.** This catches missing
  imports (`NameError` at runtime), unused imports, and syntax issues that tests
  may not surface immediately.
  ```bash
  flake8 .   # what CI runs — lints the whole repo, not just changed files
  ```
  Notes:
  - If `flake8` is **not** installed, add it first (`pip install flake8`).
  - CI runs `flake8 .` (see `.github/workflows/linting.yml`), so lint the whole
    repo — checking only your file can miss violations CI will catch.
  - The line-length limit is **79** (E501); config and excludes live in
    `.flake8`. Skill asset templates (`benchopt/skills/**/*.py`) are linted too.
- Run the relevant test suite after edits to confirm nothing regresses.
  - `pytest` and the other test deps come from the `test` extra:
    `pip install -e .[test]`. `flake8` is separate (`pip install flake8`).
  - When running benchopt's own suite, `--skip-env` skips tests that build a
    conda env and makes local runs much faster
    (`pytest benchopt/... --skip-env`).

## Deciding where a function belongs

- Guiding heuristics:
  - Module-level helpers used by a single class → put them just below that class in the same file (e.g. `_prepare_one` in `base.py` next to `BaseDataset`).
  - Execution unit functions analogous to `run_one_solver` → `runner.py`.
  - Generic utilities reused across modules → `benchopt/utils/`.
  - Do **not** put prepare/dataset logic in `benchmark.py` when `base.py` already owns that domain.

## Minimal edits

- Only touch lines directly required by the task. Do not reformat, rename, or add docstrings to surrounding code that was not part of the request.
- When a refactor touches multiple files, list the files and the nature of each change first, so the scope is explicit before you start.

## Comments and prose

- Keep comments short — one line by default; reserve longer explanations for
  genuinely subtle code. Don't narrate the obvious.
- Describe what the code does now. Don't document antipatterns or past choices
  that were overturned — especially designs that never reached main.
- The same restraint applies to reviews, issues, and PR descriptions: long text
  is hard to read without a clear reason. Lead with the point.

## Submitting a PR

See [Scoping Issues & PRs](./issues_and_prs.md) for PR scope, commit messages,
the what's new entry, and issue/review conventions.
