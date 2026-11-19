# Agent skills in this repo

This repo has its own agent-skills system, separate from any personal
ai-skills setup you may have configured elsewhere:

- `.agents/skills/benchopt-contributor/` — how to work on the benchopt
  library itself (tests, docs, CLI, contributor gotchas).
- `benchopt/skills/using-benchopt/` — the benchmark-*authoring* skill,
  packaged with benchopt and distributed via `benchopt sync-skills`.

**Before editing any file under either path, load the `benchopt-contributor`
skill via the Skill tool first** — it documents how the two bundles relate
and the "update the skill in the same PR as the code it describes" rule.
A personal ai-skills setup is a fine complement, but it won't know this
repo's specific conventions (packaging, `sync-skills`, version-stamping), so
check for `benchopt-contributor` here too.
