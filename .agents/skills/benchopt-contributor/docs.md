# Updating Documentation — benchopt

## When To Use

- Editing `doc/*.rst` content or section structure.
- Updating snippets/commands shown to users.
- Adding or adjusting sphinx-design blocks (dropdowns, cards, tabs).
- Verifying that rendered HTML matches intent before merge.
- Updating an agent skill after a code/CLI/convention change (see
  *Keeping the agent skills in sync* below).

## Documentation structure

The docs are organised into three progressive sections plus an examples
gallery, linked from `doc/index.rst` (both as grid cards and in the `toctree`
at the bottom of that file):

- **`get_started.rst`** (`:ref:\`get_started\``) — overview / onboarding:
  *Installation*, *Run an existing benchmark*, *Create your own benchmark*, and
  a *Key features* tour. Keep it short; it links into the deeper sections.
- **`benchmark_workflow/`** (`:ref:\`benchmark_workflow\``) — how to use
  benchopt end to end: `write_benchmark`, `run_benchmark`,
  `manage_benchmark_results`, `test_benchmark`. These cover the common workflow
  and point to the user guide for advanced features.
- **`user_guide/`** (`:ref:\`user_guide\``) — in-depth reference: `authoring`,
  `running`, `testing`, `agent_skills`, and the API/CLI `reference`.
- **`auto_examples/`** — the Examples gallery, generated from `examples/` by
  sphinx-gallery (see below). Do not edit by hand.

When adding a page, place it in the section matching its depth and update that
section's `index.rst` `toctree` (and the bottom `toctree` in `doc/index.rst`).

## Keeping the agent skills in sync

benchopt ships two agent-skill bundles, and they are **documentation that is
neither built nor tested** — nothing catches drift, so a stale skill silently
feeds an agent a wrong flag, a renamed API, or a dropped convention:

- **`.agents/skills/benchopt-contributor/`** — this skill, for contributing to
  the library itself.
- **`benchopt/skills/using-benchopt/`** — the benchmark-*authoring* skill,
  packaged with benchopt and installed into a benchmark or globally with
  `benchopt sync-skills`.

Treat them like the `.rst` docs: when a PR changes something a skill describes,
update the matching skill file **in the same PR**.

- CLI flags/options, run/install/plot behaviour → `using-benchopt`
  (`cli-reference.md`, `run.md`, `results.md`, …).
- Public API or base-class contract (`Objective` / `Solver` / `Dataset`) →
  `using-benchopt` `add-objective.md` / `add-solver.md` / `add-dataset.md`.
- Contributor workflow, test helpers, gotchas → this skill (`tests.md`,
  `general.md`, `gotchas.md`, `docs.md`).

The `using-benchopt` `SKILL.md` records the benchopt version it was synced from
and warns users when their installed version differs, prompting a re-run of
`benchopt sync-skills`. Shipping the skill update alongside the code keeps that
signal honest — otherwise users re-sync only to get the same stale guidance.

## Standard Workflow

```bash
sphinx-build -E -b html doc doc/_build/html
```

1. Locate the target page and nearby references (`toctree`, links, includes).
2. Make minimal content edits first, then structural/styling adjustments only if needed.
3. Rebuild docs with `-E` to avoid stale-cache confusion.
4. Open the built page and verify both folded and expanded states for interactive blocks.
5. Check for warnings and fix broken links, malformed directives, and indentation issues.

## File Map

- `doc/`: Sphinx source.
- `doc/index.rst`: landing page (grid cards + bottom `toctree`).
- `doc/get_started.rst`: onboarding overview page.
- `doc/benchmark_workflow/`, `doc/user_guide/`: the two deeper sections, each
  with its own `index.rst` + `toctree`.
- `examples/run_*.py`: gallery sources; `doc/auto_examples/`: generated gallery
  (do not edit by hand).
- `doc/conf.py`: extension, sphinx-gallery, and static asset registration.
- `doc/_static/style.css`: visual overrides.
- `doc/_static/benchopt.js`: behavior that cannot be done in pure CSS.
- `doc/_build/html/`: rendered output to inspect.

## Examples (sphinx-gallery)

Examples live in `examples/` as `run_*.py` scripts and are rendered to
`doc/auto_examples/` by `sphinx_gallery` (configured in `doc/conf.py`:
`examples_dirs='../examples'`, `gallery_dirs='auto_examples'`,
`filename_pattern=r'/run_.*\.py'`, and `ignore_pattern=r'.*_benchmark/'` so the
benchmark folders under `examples/` are not treated as scripts). Scripts use
`# %%` cell markers with reST-formatted comments.

Two helpers from `benchopt.helpers.run_examples` make examples render cleanly:

- **`ExampleBenchmark(base=..., name=..., ignore=[...])`** — load/build a
  benchmark from `examples/<base>/`; exposes `.benchmark_dir` and an
  `.update(...)` method, and renders its files via `_repr_html_` when evaluated
  in a cell.
- **`benchopt_cli("run <dir> -n 20 -r 2")`** — run a benchopt CLI command from
  inside an example; under a Sphinx build it embeds the resulting HTML output
  (results table / plots) into the page.

```python
from benchopt.helpers.run_examples import ExampleBenchmark, benchopt_cli

benchmark = ExampleBenchmark(base="minimal_benchmark", name="minimal_benchmark")
benchmark  # renders the benchmark files in the page
# %%                                                # renders the files
benchopt_cli(f"run {benchmark.benchmark_dir} -n 20 -r 2")  # runs + embeds output
```

The gallery executes these scripts at build time, so keep them fast (small
`-n`/`-r`).

## Review Checklist

- Page builds without new warnings/errors.
- Command examples are copy-pastable and up to date.
- Dropdown/tab content is readable in both folded and open states.
- No accidental behavior regressions in existing sections.
- Text is concise and user-facing language is clear.
- When a code change renames a public API, update every `.rst` that mentions it
  — the build won't flag prose that references the old name.
- Likewise update the agent skills (see *Keeping the agent skills in sync*) — a
  stale skill is caught by no build or test.

## Notes For Dropdown Content

- `:class-container:` on a `.. dropdown::` adds class on `<details>`.
- Closed `<details>` hides body content by browser behavior.
- If folded-only header content is needed, place it in the summary/header (or inject via JS).

Use `python -m http.server 8000 --directory doc/_build/html` for quick local browsing.
