# benchopt Implementation Design Guidelines

## Finding code in the codebase

- When searching for where something is implemented (a function, a pattern, a hook) and the first search returns nothing, **ask the user directly** rather than continuing to search. They will know immediately.
- Do not make more than two search attempts before asking.

## Validating changes

- **Always run `flake8` on modified files before declaring a change done.** This catches missing imports (`NameError` at runtime), unused imports, and syntax issues that tests may not surface immediately.
  ```bash
  flake8 benchopt/path/to/modified_file.py
  ```
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
