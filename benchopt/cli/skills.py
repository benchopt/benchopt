import shutil
import click
from pathlib import Path
from importlib import resources

from benchopt.utils.terminal_output import colorify
from benchopt.utils.terminal_output import GREEN, BLUE, RED, TICK


SKILL_NAME = "using-benchopt"

# Canonical, cross-harness skills directory (Agent Skills open standard). Read
# natively by Codex, Gemini CLI, Copilot/VS Code, Cursor, OpenCode, ...
AGENTS_SKILLS_DIR = Path(".agents") / "skills"

# Claude Code does not read .agents/skills yet (anthropics/claude-code#31005),
# so we mirror the skill here via symlink (or copy as a fallback).
CLAUDE_SKILLS_DIR = Path(".claude") / "skills"


def _source_skill():
    """Return the path to the packaged using-benchopt skill."""
    return resources.files("benchopt") / "skills" / SKILL_NAME


def _link_or_copy(target, source):
    """Symlink ``target`` -> ``source``; fall back to a recursive copy."""
    if target.exists() or target.is_symlink():
        if target.is_symlink() or target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)
    try:
        target.symlink_to(source.resolve(), target_is_directory=True)
        return "symlink"
    except (OSError, NotImplementedError):
        shutil.copytree(source, target)
        return "copy"


@click.group(name="Skills", help="Manage benchopt agent skills.")
def skills():
    pass


@skills.command(
    name="sync-skills",
    help="Sync the benchopt agent skill into a benchmark (or globally).",
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
def sync_skills(benchmark, global_, no_claude):
    base = Path.home() if global_ else Path(benchmark)
    agents_dir = base / AGENTS_SKILLS_DIR
    claude_dir = base / CLAUDE_SKILLS_DIR

    src = _source_skill()
    dest = colorify(str(agents_dir), BLUE)

    agents_dir.mkdir(parents=True, exist_ok=True)
    target = agents_dir / SKILL_NAME
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(src, target)
    click.echo(f"Synced {colorify(SKILL_NAME, GREEN)} into {dest}")

    if not no_claude:
        claude_dir.mkdir(parents=True, exist_ok=True)
        kind = _link_or_copy(claude_dir / SKILL_NAME, target)
        click.echo(f"Claude mirror ({kind}) at {colorify(str(claude_dir), BLUE)}")

    click.echo(colorify(f"{TICK} Done.", GREEN))
