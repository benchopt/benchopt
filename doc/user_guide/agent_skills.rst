.. _agent_skills:

AI agent skills
===============

Benchopt ships a small library of **agent skills** — short, structured
documents that teach an AI coding agent how to work with benchopt (authoring a
benchmark, adding a solver or dataset, running benchmarks). They follow the
`Agent Skills open standard <https://agentskills.io>`_ (``SKILL.md`` files) and
are read by most coding agents: Codex, Gemini CLI, GitHub Copilot / VS Code,
Cursor, and others.

Because the skills ship inside the benchopt package, they always match your
installed version: ``pip install -U benchopt`` followed by ``benchopt
sync-skills`` keeps them up to date.

Installing the skills
---------------------

Run ``sync-skills`` from a benchmark repository to install the shared skills
into it:

.. prompt:: bash $

    benchopt sync-skills

This writes the skills into ``.agents/skills/`` (the cross-harness standard
location) and mirrors them under ``.claude/skills/`` for Claude Code, which
does not yet read ``.agents/skills/`` natively. The mirror uses symlinks where
available and falls back to copies otherwise (e.g. Windows without developer
mode).

To install the skills once for your whole machine instead, use ``--global``,
which targets ``~/.agents/skills/``:

.. prompt:: bash $

    benchopt sync-skills --global

Useful options:

- ``--dry-run``: show what would change without writing anything.
- ``--no-claude``: skip the ``.claude/skills`` mirror.

Idempotent updates
-----------------

``sync-skills`` records what it installed in a manifest
(``.agents/skills/.benchopt-skills-manifest.json``). Re-running it is safe: it
refreshes the shared skills and removes any that were deleted upstream, so no
orphans are left behind. Only benchopt's own skills (named with the
``benchopt-`` prefix) are ever written or removed.

Shared vs. repo-specific skills
------------------------------

A benchmark can keep its own skills next to the synced ones. The convention:

- **Shared skills** (``benchopt-*``) come from ``benchopt sync-skills`` and are
  managed by benchopt. Do **not** edit them inside a benchmark repo — fix them
  upstream in benchopt and release. They are typically gitignored::

      .agents/skills/benchopt-*
      .claude/skills/benchopt-*

- **Repo-specific skills** use any other name, live in ``.agents/skills/``, and
  are committed to the benchmark repo. ``sync-skills`` never touches them.

After upgrading benchopt, re-run ``benchopt sync-skills`` to pick up the
matching skills.
