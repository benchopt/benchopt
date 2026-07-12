# Scoping Issues & PRs

## Keep a PR to one concern

- A PR should do one thing. If a review comment opens a genuinely separate
  feature, don't bolt it on — it widens the diff and invites bikeshedding on
  already-reviewed work. Open a dedicated issue and link it.
- Flag changes unrelated to the PR's stated purpose (an incidental refactor, a
  drive-by fix): justify it in the description or move it to its own PR.
- Before committing, show `git diff --stat` then the full diff. Don't commit or
  push unless the user asks.

## Opening a PR

- Work through the PR template checklist (`.github/pull_request_template.md`):
  documentation for new features, a unit test, and a what's new entry.
- Commit messages: single line, imperative, prefixed to match recent `git log`
  (`ENH` / `FIX` / `TST` / `PERF` / `DOC` / `RFC`).
- **What's new entry** — add a `doc/whats_new.rst` entry for any user-facing
  change. Put it under the in-development version, in the matching section
  (`CLI` / `API` / `PLOT` / `TST` / `FIX` / `DOC`), ending with
  ``By `Your Name`_ (:gh:`NNN`)``. If a follow-up PR extends an existing entry,
  update that bullet and list both PRs (``:gh:`959`, :gh:`980```) rather than
  adding a near-duplicate.

## Writing an issue

- Lead with one short motivation paragraph (why it matters, a concrete case),
  merged with what we want — not separate "Background" + "Goal" sections.
- For a design/feature issue, follow with a short **Key questions** bullet list
  of the decisions to settle, not a spec.
- Distinguish a *follow-up* (extends a PR — reference it, e.g. "Follow-up to
  #935") from an *orthogonal* issue (don't link a PR it doesn't depend on).

## Reviewing a PR

- Group findings by severity: **Blocking** / **Should-fix** / **Nits** /
  **Positives**, so the author can triage the one or two things that actually
  block separately from cosmetic nits.
