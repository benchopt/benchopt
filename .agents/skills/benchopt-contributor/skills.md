# Adding Agent Skills — benchopt

## Where skills live

| Tier | Lives in | Packaged? |
| --- | --- | --- |
| **Usage** — how to use benchopt / author a benchmark | `benchopt/skills/using-benchopt/` | yes (pip package data) |
| **Library/contributor** — how to work on the benchopt codebase | `.agents/skills/` in this repo | no |
| **Benchmark-specific** — tied to one benchmark | `.agents/skills/` in that benchmark repo | no |

Only the usage tier is distributed, by `benchopt sync-skills`
(`benchopt/skills/README.md`). Updating a skill in the same PR as the code it
describes is a hard rule — see [Documentation](./docs.md).

## Editing the usage skill

`benchopt/cli/skills.py` ships exactly one skill, named by the module constant
`SKILL_NAME = "using-benchopt"`. There is no folder scan: adding a *second*
usage skill is a code change (`_source_skill` and `sync_skills` must iterate),
not a drop-in folder.

Constraints that only bite at sync time or in CI:

- `SKILL.md` must keep the `__BENCHOPT_VERSION__` placeholder
  (`VERSION_PLACEHOLDER`). `_finalize_skill` swaps it for the installed version
  so the agent can detect a stale skill; `test_sync_stamps_version` fails if it
  is gone.
- Write benchopt doc links as `https://benchopt.github.io/stable/...` — sync
  retargets `stable` at the installed version's docs. Every such URL is
  HTTP-checked by `test_skill_doc_url_valid` (`-m network`), so a typo'd or
  renamed page fails CI.
- Finalization only walks `*.md`, so a version stamp or doc link inside
  `scripts/` or `assets/` is never rewritten.
- New support files ship only if they match a package-data glob in
  `pyproject.toml` (`"benchopt.skills"`: `**/*.md`, `**/scripts/*`,
  `**/references/*`, `**/assets/*`). Another layout needs a new glob.

## Verifying

```bash
pytest benchopt/cli/tests/test_cmd_sync_skills.py
benchopt sync-skills          # into ./.agents/skills/ (+ .claude/skills mirror)
```

Sync is idempotent: it removes and rewrites `using-benchopt` in place and
leaves every other entry in `.agents/skills/` alone.

## Notes

- **Never edit the synced copy** in a benchmark repo — the next sync overwrites
  it. Fix `benchopt/skills/using-benchopt/` here and release.
- Claude Code does not read `.agents/skills/` yet, so sync also mirrors the
  skill under `.claude/skills/` (symlink, copy as fallback); `--no-claude`
  skips the mirror.
- User-facing documentation: `doc/user_guide/agent_skills.rst`.
