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
  - `pytest` and the other test deps come from the `test` extra:
    `uv pip install -e .[test]`. `flake8` is separate (`uv pip install flake8`).
  - When running benchopt's own suite, `--skip-env` skips tests that build a
    conda env and `--skip-install` skips solver installs that slow CI — both
    make local runs much faster
    (`pytest benchopt/... --skip-env --skip-install`).

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
