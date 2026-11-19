.. _agent_skills:

AI agent skills
===============

Benchopt ships an **agent skill** — a small set of structured documents that
teach an AI coding agent how to work with benchopt (authoring a benchmark,
adding a solver or dataset, running benchmarks, exploring results). It follows
the `Agent Skills open standard <https://agentskills.io>`_ (``SKILL.md`` files)
and is read by most coding agents: Codex, Gemini CLI, GitHub Copilot / VS Code,
Cursor, and others.

Because the skill ships inside the benchopt package, it always matches your
installed version: ``pip install -U benchopt`` followed by ``benchopt
sync-skills`` keeps it up to date.

Installing the skill
--------------------

Run ``sync-skills`` from a benchmark repository to install the skill into it:

.. prompt:: bash $

    benchopt sync-skills

This writes the skill into ``.agents/skills/`` (the cross-harness standard
location) and mirrors it under ``.claude/skills/`` for Claude Code, which does
not yet read ``.agents/skills/`` natively. The mirror uses symlinks where
available and falls back to copies otherwise (e.g. Windows without developer
mode).

To install the skill once for your whole machine instead, use ``--global``,
which targets ``~/.agents/skills/``:

.. prompt:: bash $

    benchopt sync-skills --global

Use ``--no-claude`` to skip the ``.claude/skills`` mirror.

Keeping the skill up to date
----------------------------

``sync-skills`` copies the packaged skill and stamps the current benchopt
version into it. Re-running it is safe and idempotent: it refreshes
``using-benchopt`` in place and leaves any other (repo-specific) skills in
``.agents/skills/`` untouched.

After upgrading benchopt, re-run ``benchopt sync-skills`` to pick up the
matching skill. The skill instructs the agent to compare its stamped version
against ``benchopt --version`` and warn you when a refresh is needed.
