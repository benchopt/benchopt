# benchopt Implementation Design Guidelines

## Finding code in the codebase

- When searching for where something is implemented (a function, a pattern, a hook) and a couple of targeted searches turn up nothing, **ask the user directly** rather than spiraling into more searches. They will know immediately.

## Validating changes

- **Always run `flake8` before declaring a change done.** This catches missing
  imports (`NameError` at runtime), unused imports, and syntax issues that tests
  may not surface immediately.
  ```bash
  flake8 .   # what CI runs — lints the whole repo, not just changed files
  ```
  Notes:
  - `flake8` is **not** in the base env; install it first if missing
    (`uv pip install flake8`).
  - CI runs `flake8 .` (see `.github/workflows/linting.yml`), so lint the whole
    repo — checking only your file can miss violations CI will catch.
  - The line-length limit is **79** (E501); config and excludes live in
    `.flake8`. Skill asset templates (`benchopt/skills/**/*.py`) are linted too.
- Run the relevant test suite after edits to confirm nothing regresses.

## Deciding where a function belongs

- **Propose placement before implementing or moving anything.** State the candidate locations, give one sentence of rationale for each, and ask the user to confirm.
- Guiding heuristics:
  - Module-level helpers used by a single class → put them just below that class in the same file (e.g. `_prepare_one` in `base.py` next to `BaseDataset`).
  - Execution unit functions analogous to `run_one_solver` → `runner.py`.
  - Generic utilities reused across modules → `benchopt/utils/`.
  - Do **not** put prepare/dataset logic in `benchmark.py` when `base.py` already owns that domain.

## Minimal edits

- Only touch lines directly required by the task. Do not reformat, rename, or add docstrings to surrounding code that was not part of the request.
- When a refactor touches multiple files, list the files and the nature of each change before starting, and get confirmation if the scope feels large.

## Submitting a PR

- **Add a `doc/whats_new.rst` entry** for any user-facing change (the PR
  template has a checkbox for it). Put it under the in-development version,
  in the matching section (`CLI` / `API` / `PLOT` / `TST` / `FIX` / `DOC`),
  ending with ``By `Your Name`_ (:gh:`NNN`)``. If a follow-up PR extends an
  existing entry, update that bullet and list both PRs (``:gh:`959`, :gh:`980```)
  rather than adding a near-duplicate.
