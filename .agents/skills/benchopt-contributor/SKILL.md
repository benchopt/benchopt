---
name: benchopt-contributor
description: >
  Conventions for contributing to the benchopt codebase itself: implementation
  design, writing tests, and updating the docs. Use when implementing features,
  moving code, writing tests, or editing docs in the benchopt repo. Benchmark
  *authoring* guidance ships separately via `benchopt sync-skills`.
---

# benchopt contributor skills

Guidelines for working on the **benchopt library** itself. For authoring a
*benchmark* (datasets/solvers/objective), use the `using-benchopt` skill that
ships with benchopt — run `benchopt sync-skills` to install it.

- [General implementation design](./general.md) — where to put code, how to validate changes, minimal-edit discipline, writing concise comments, and when to ask the user.
- [Scoping issues & PRs](./issues_and_prs.md) — keeping a PR to one concern, commit/what's-new conventions, and how to write issues and review PRs.
- [Tests](./tests.md) — writing CLI tests in `benchopt/cli/tests/` with `temp_benchmark`, `CaptureCmdOutput`, mocking, and parametrize patterns.
- [Documentation](./docs.md) — Sphinx workflow: editing `doc/*.rst`, rebuilding with `-E`, verifying dropdown/tab content.
