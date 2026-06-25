# benchopt shared agent skills

This directory is the **source of truth** for the *usage* agent skills that
benchopt distributes to benchmark repositories. Each subfolder is one skill in
the [Agent Skills open standard](https://agentskills.io) (`SKILL.md` format),
and every shared skill name carries the `benchopt-` prefix.

These skills ship as **package data** inside the `benchopt` pip package, so the
skills you get always match your installed benchopt version. Install them into a
project (or globally) with:

```bash
benchopt sync-skills            # into ./.agents/skills/ (+ Claude symlinks)
benchopt sync-skills --global   # into ~/.agents/skills/
```

## Tiers (where skills live)

- **Usage skills (here):** how to *use* benchopt / author a benchmark. Shipped
  as package data and distributed via `benchopt sync-skills`. Prefixed
  `benchopt-`.
- **Library/contributor skills:** how to work on the benchopt codebase itself.
  Live in this repo's own `.agents/skills/` (committed, **not** packaged).
- **Benchmark-specific skills:** live in the benchmark repo's `.agents/skills/`,
  committed, with no `benchopt-` prefix.

## Distribution model

`.agents/skills/` is the canonical, cross-harness location: Codex, Gemini CLI,
GitHub Copilot / VS Code, Cursor, OpenCode, OpenHands and others read it
natively. Claude Code does **not** read `.agents/skills/` yet
(anthropics/claude-code#31005), so `sync-skills` additionally creates
per-skill symlinks under `.claude/skills/` (falling back to copies where
symlinks are unavailable, e.g. Windows without developer mode).

A manifest (`.agents/skills/.benchopt-skills-manifest.json`) records what was
written so re-running is idempotent and upstream-deleted skills are cleaned up
instead of leaving orphans. Only `benchopt-*` entries are ever touched —
repo-specific skills next to them are left alone.

**Never edit `benchopt-*` skills inside a benchmark repo** — fix them in the
benchopt repo and release.
Re-run `benchopt sync-skills` after upgrading benchopt to update.
