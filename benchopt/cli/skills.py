import os
import json
import shutil
import click
from pathlib import Path
from importlib import resources

from benchopt import __version__
from benchopt.utils.terminal_output import colorify
from benchopt.utils.terminal_output import GREEN, BLUE, RED, TICK, CROSS


# Prefix that identifies a skill as managed (synced) by benchopt. Only folders
# carrying this prefix are ever written or removed by ``sync-skills``; anything
# else in the target directory (repo-specific skills) is left untouched.
SKILL_PREFIX = "benchopt-"

# Canonical, cross-harness skills directory (Agent Skills open standard). Read
# natively by Codex, Gemini CLI, Copilot/VS Code, Cursor, OpenCode, ...
AGENTS_SKILLS_DIR = Path(".agents") / "skills"

# Claude Code does not read .agents/skills yet (anthropics/claude-code#31005),
# so we mirror each synced skill here via symlink (or copy as a fallback).
CLAUDE_SKILLS_DIR = Path(".claude") / "skills"

MANIFEST_NAME = ".benchopt-skills-manifest.json"


def _source_skills_dir():
    """Return the packaged source-of-truth skills directory."""
    return resources.files("benchopt") / "skills"


def _iter_source_skills():
    """Yield (name, path) for each packaged ``benchopt-*`` skill folder."""
    src = _source_skills_dir()
    for entry in sorted(src.iterdir(), key=lambda p: p.name):
        if not entry.name.startswith(SKILL_PREFIX):
            continue
        if (entry / "SKILL.md").is_file():
            yield entry.name, entry


def _read_manifest(agents_dir):
    manifest_path = agents_dir / MANIFEST_NAME
    if not manifest_path.exists():
        return {"benchopt_version": None, "skills": []}
    with open(manifest_path) as f:
        return json.load(f)


def _write_manifest(agents_dir, skills):
    manifest = {"benchopt_version": __version__, "skills": sorted(skills)}
    with open(agents_dir / MANIFEST_NAME, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")


def _link_or_copy(target, source):
    """Symlink ``target`` -> ``source``; fall back to a recursive copy.

    Returns the kind of mirror created: ``"symlink"`` or ``"copy"``. Used for
    the Claude adapter where native .agents/skills support is missing.
    """
    if target.exists() or target.is_symlink():
        if target.is_symlink() or target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)
    try:
        target.symlink_to(source.resolve(), target_is_directory=True)
        return "symlink"
    except (OSError, NotImplementedError):
        # e.g. Windows without developer mode: copy instead.
        shutil.copytree(source, target)
        return "copy"


@click.group(name="Skills", help="Manage benchopt agent skills.")
def skills():
    pass


@skills.command(
    name="sync-skills",
    help="Sync benchopt's shared agent skills into a benchmark (or globally).",
)
@click.argument(
    "benchmark", default=".", type=click.Path(exists=True),
)
@click.option(
    "--global", "global_", is_flag=True,
    help="Install into ~/.agents/skills instead of the benchmark directory.",
)
@click.option(
    "--no-claude", is_flag=True,
    help="Do not create the .claude/skills mirror for Claude Code.",
)
@click.option(
    "--dry-run", is_flag=True,
    help="Show what would change without writing anything.",
)
def sync_skills(benchmark, global_, no_claude, dry_run):
    base = Path.home() if global_ else Path(benchmark)
    agents_dir = base / AGENTS_SKILLS_DIR
    claude_dir = base / CLAUDE_SKILLS_DIR

    source_skills = dict(_iter_source_skills())
    if not source_skills:
        click.echo(colorify("No packaged benchopt skills found.", RED))
        return

    prev = _read_manifest(agents_dir)
    prev_skills = set(prev.get("skills", []))
    new_skills = set(source_skills)

    stale = sorted(prev_skills - new_skills)
    added = sorted(new_skills - prev_skills)
    updated = sorted(new_skills & prev_skills)

    dest = colorify(str(agents_dir), BLUE)
    click.echo(f"Syncing {len(new_skills)} benchopt skill(s) into {dest}")
    if dry_run:
        for name in added:
            click.echo(f"  + {name} (new)")
        for name in updated:
            click.echo(f"  ~ {name} (update)")
        for name in stale:
            click.echo(colorify(f"  - {name} (remove, deleted upstream)", RED))
        click.echo("Dry run: nothing written.")
        return

    agents_dir.mkdir(parents=True, exist_ok=True)

    # Remove skills that disappeared upstream (only our prefixed ones).
    for name in stale:
        target = agents_dir / name
        if target.is_dir():
            shutil.rmtree(target)
        claude_target = claude_dir / name
        if claude_target.is_symlink() or claude_target.exists():
            if claude_target.is_dir() and not claude_target.is_symlink():
                shutil.rmtree(claude_target)
            else:
                claude_target.unlink()
        click.echo(colorify(f"  {CROSS} removed {name}", RED))

    # Write/refresh current skills.
    for name, src_path in source_skills.items():
        target = agents_dir / name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(src_path, target)
        click.echo(colorify(f"  {TICK} {name}", GREEN))

    _write_manifest(agents_dir, new_skills)

    # Claude adapter: mirror each skill under .claude/skills.
    if not no_claude:
        claude_dir.mkdir(parents=True, exist_ok=True)
        kinds = set()
        for name in source_skills:
            kind = _link_or_copy(claude_dir / name, agents_dir / name)
            kinds.add(kind)
        how = "/".join(sorted(kinds)) if kinds else "none"
        mirror = colorify(str(claude_dir), BLUE)
        click.echo(f"Claude mirror ({how}) at {mirror}")

    click.echo(colorify(f"{TICK} Done.", GREEN))
