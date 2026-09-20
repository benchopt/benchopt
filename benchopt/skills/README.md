# benchopt shared agent skills

This directory is the **source of truth** for the *usage* agent skill that
benchopt distributes to benchmark repositories: `using-benchopt/`, written in
the [Agent Skills open standard](https://agentskills.io) (`SKILL.md` format).

It ships as **package data** inside the `benchopt` pip package, so the skill
you get always matches your installed benchopt version. Install it into a
project (or globally) with:

```bash
benchopt sync-skills            # into ./.agents/skills/ (+ Claude mirror)
benchopt sync-skills --global   # into ~/.agents/skills/
```

## Tiers (where skills live)

- **Usage skill (here):** how to *use* benchopt / author a benchmark. Shipped
  as package data and distributed via `benchopt sync-skills`.
- **Library/contributor skills:** how to work on the benchopt codebase itself.
  Live in this repo's own `.agents/skills/` (committed, **not** packaged).
- **Benchmark-specific skills:** live in the benchmark repo's `.agents/skills/`,
  committed, alongside the synced copy.

## Distribution model

`.agents/skills/` is the canonical, cross-harness location: Codex, Gemini CLI,
GitHub Copilot / VS Code, Cursor, OpenCode, OpenHands and others read it
natively. Claude Code does **not** read `.agents/skills/` yet
(anthropics/claude-code#31005), so `sync-skills` additionally mirrors the skill
under `.claude/skills/` (symlink, falling back to a copy where symlinks are
unavailable, e.g. Windows without developer mode). `--no-claude` skips it.

Sync removes and rewrites `using-benchopt` in place, so re-running is
idempotent; every other entry in `.agents/skills/` is left untouched. It also
stamps the installed benchopt version into the skill and retargets the doc
links at the matching version's documentation.

**Never edit the synced `using-benchopt` copy inside a benchmark repo** — the
next sync overwrites it. Fix it here, in the benchopt repo, and release.
Re-run `benchopt sync-skills` after upgrading benchopt to update.

Contributor-facing details (version placeholder, packaging globs, tests) are in
`.agents/skills/benchopt-contributor/skills.md`.
