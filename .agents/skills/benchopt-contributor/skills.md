# Adding Agent Skills — benchopt

## When To Use

- Adding or editing a *usage* skill that benchopt ships to benchmark repos.
- Working on the skill distribution machinery (`benchopt sync-skills`).
- Deciding **where** a new skill belongs (which tier).

## The three tiers

Pick the tier first — it decides the location, the prefix, and whether the
skill is packaged.

| Tier | Lives in | Prefix | Packaged? |
| --- | --- | --- | --- |
| **Usage** — how to *use* benchopt / author a benchmark | `benchopt/skills/benchopt-<name>/` | `benchopt-` | yes (pip package data) |
| **Library/contributor** — how to work on the benchopt codebase | this repo's `.agents/skills/` | none | no (committed only) |
| **Benchmark-specific** — tied to one benchmark | benchmark repo's `.agents/skills/` | none | no (committed in that repo) |

`benchopt/skills/README.md` is the source-of-truth doc for the usage tier —
read it (and keep it in sync) when touching this area. The contributor tier is
where *this* skill lives.

## Adding a usage skill

Usage skills are the ones distributed with `benchopt sync-skills`. To add one:

1. Create a folder `benchopt/skills/benchopt-<name>/` with a `SKILL.md`
   carrying the `benchopt-` prefix. The folder name **is** the skill name.
2. Give `SKILL.md` the standard frontmatter:
   ```markdown
   ---
   name: benchopt-<name>
   description: >
     One or two sentences on what the skill covers and when to use it.
   ---
   ```
3. Discovery is **folder-based**, not registered anywhere: `_iter_source_skills`
   in `benchopt/cli/skills.py` yields every `benchopt-*` subfolder that contains
   a `SKILL.md`. No list to update — drop the folder in and it ships.
4. Supporting files are shipped via the package-data globs in `pyproject.toml`
   (`[tool.setuptools.package-data]` → `"benchopt.skills"`): `**/SKILL.md`,
   `**/*.md`, `**/scripts/*`, `**/references/*`, `**/assets/*`. Extra `.md`
   pages and `scripts/`, `references/`, `assets/` subdirs are covered; if you
   need a different support layout, add a matching glob there.

## Verifying

- `benchopt/cli/tests/test_cmd_sync_skills.py` auto-discovers all `benchopt-*`
  skills via `_iter_source_skills`, so a new skill is exercised by the existing
  tests automatically; `test_packaged_skills_present` sanity-checks that skills
  are packaged and discoverable.
- Run a local sync to eyeball the result:
  ```bash
  benchopt sync-skills --dry-run    # show added/updated/removed, write nothing
  benchopt sync-skills              # into ./.agents/skills/ (+ .claude mirror)
  ```
- See [Tests](./tests.md) for the CLI-test conventions if you add a dedicated
  test.

## Notes

- **Never edit `benchopt-*` skills inside a benchmark repo** — they are synced
  copies. Fix them under `benchopt/skills/` here and release.
- `sync-skills` is idempotent via `.agents/skills/.benchopt-skills-manifest.json`
  and only ever touches `benchopt-*` entries, leaving repo-specific skills alone.
- Claude Code does not read `.agents/skills/` yet, so `sync-skills` also mirrors
  each skill under `.claude/skills/` (symlink, or copy as a fallback).
- User-facing documentation for skills lives at `doc/user_guide/agent_skills`
  (see [Documentation](./docs.md)).
