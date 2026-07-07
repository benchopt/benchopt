import shutil
import click
from pathlib import Path
from importlib import resources

from benchopt import __version__
from benchopt.utils.terminal_output import colorify
from benchopt.utils.terminal_output import GREEN, BLUE, TICK


SKILL_NAME = "using-benchopt"

# Placeholder in the packaged SKILL.md, replaced with the benchopt version at
# sync time so the agent can detect a stale skill.
VERSION_PLACEHOLDER = "__BENCHOPT_VERSION__"

# Canonical, cross-harness skills directory (Agent Skills open standard). Read
# natively by Codex, Gemini CLI, Copilot/VS Code, Cursor, OpenCode, ...
AGENTS_SKILLS_DIR = Path(".agents") / "skills"

# Claude Code does not read .agents/skills yet (anthropics/claude-code#31005),
# so we mirror the skill here via symlink (or copy as a fallback).
CLAUDE_SKILLS_DIR = Path(".claude") / "skills"


def _source_skill():
    """Return the path to the packaged using-benchopt skill."""
    return resources.files("benchopt") / "skills" / SKILL_NAME


def _stamp_version(skill_dir):
    """Write the current benchopt version into the copied SKILL.md."""
    skill_md = skill_dir / "SKILL.md"
    text = skill_md.read_text()
    skill_md.write_text(text.replace(VERSION_PLACEHOLDER, __version__))


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
    except (OSError, NotImplementedError) as symlink_err:
        # Symlinks may be unsupported (Windows without developer mode,
        # FAT/exFAT, some network mounts); fall back to a plain copy.
        try:
            shutil.copytree(source, target)
        except OSError as copy_err:
            raise OSError(
                f"Could not mirror skill to {target}: symlink failed "
                f"({symlink_err}) and copy failed ({copy_err})."
            ) from copy_err
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
    if global_ and benchmark != ".":
        raise click.UsageError(
            "Cannot use --global with a benchmark path argument."
        )
    base = Path.home() if global_ else Path(benchmark)
    agents_dir = base / AGENTS_SKILLS_DIR
    claude_dir = base / CLAUDE_SKILLS_DIR

    dest = colorify(str(agents_dir), BLUE)

    agents_dir.mkdir(parents=True, exist_ok=True)
    target = agents_dir / SKILL_NAME
    if target.exists() or target.is_symlink():
        if target.is_symlink() or target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)
    # ``as_file`` materializes the packaged skill to a real path (extracting
    # from a zip/wheel if needed) so ``copytree`` works for any install type.
    with resources.as_file(_source_skill()) as src:
        shutil.copytree(src, target)
    _stamp_version(target)
    click.echo(f"Synced {colorify(SKILL_NAME, GREEN)} into {dest}")

    if not no_claude:
        claude_dir.mkdir(parents=True, exist_ok=True)
        kind = _link_or_copy(claude_dir / SKILL_NAME, target)
        click.echo(f"Claude mirror ({kind}) at {colorify(str(claude_dir), BLUE)}")

    click.echo(colorify(f"{TICK} Done.", GREEN))
