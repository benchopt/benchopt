import re
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

# Skill doc links ship pointing at the ``stable`` docs; at sync time we
# retarget them at the installed version's docs (see ``_doc_url_version``).
STABLE_DOC_PREFIX = "benchopt.github.io/stable/"

# Only final releases (``X.Y`` / ``X.Y.Z``) publish version-specific docs; dev
# builds and pre-releases only exist under ``/dev/``.
_RELEASE_RE = re.compile(r"^\d+\.\d+(\.\d+)?$")

# Canonical, cross-harness skills directory (Agent Skills open standard). Read
# natively by Codex, Gemini CLI, Copilot/VS Code, Cursor, OpenCode, ...
AGENTS_SKILLS_DIR = Path(".agents") / "skills"

# Claude Code does not read .agents/skills yet (anthropics/claude-code#31005),
# so we mirror the skill here via symlink (or copy as a fallback).
CLAUDE_SKILLS_DIR = Path(".claude") / "skills"


def _source_skill():
    """Return the path to the packaged using-benchopt skill."""
    return resources.files("benchopt") / "skills" / SKILL_NAME


def _doc_url_version():
    """Docs path segment matching the installed version.

    Final releases publish their own docs (``/1.9.1/``); dev builds and
    pre-releases only exist under ``/dev/``.
    """
    return __version__ if _RELEASE_RE.match(__version__) else "dev"


def _finalize_skill(skill_dir):
    """Stamp the version and point doc links at the matching docs, in place."""
    doc_prefix = f"benchopt.github.io/{_doc_url_version()}/"
    for md in skill_dir.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        new = text.replace(VERSION_PLACEHOLDER, __version__)
        new = new.replace(STABLE_DOC_PREFIX, doc_prefix)
        if new != text:
            md.write_text(new, encoding="utf-8")


def _link_or_copy(target, source, prefer_symlink=True):
    """Mirror ``source`` -> ``target``, replacing any existing ``target``.

    With ``prefer_symlink`` (default) try a symlink and fall back to a
    recursive copy; with ``prefer_symlink=False`` always copy (used when
    ``source`` is a transient path, e.g. a skill materialized from the wheel).
    """
    # Remove target whether it is a symlink, a file, or a directory.
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.exists():
        shutil.rmtree(target)
    if not prefer_symlink:
        shutil.copytree(source, target)
        return "copy"
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
    # ``as_file`` materializes the packaged skill to a real path (extracting
    # from a zip/wheel if needed) so ``copytree`` works for any install type.
    with resources.as_file(_source_skill()) as src:
        _link_or_copy(target, src, prefer_symlink=False)
    _finalize_skill(target)
    click.echo(f"Synced {colorify(SKILL_NAME, GREEN)} into {dest}")

    if not no_claude:
        claude_dir.mkdir(parents=True, exist_ok=True)
        kind = _link_or_copy(claude_dir / SKILL_NAME, target)
        click.echo(
            f"Claude mirror ({kind}) at {colorify(str(claude_dir), BLUE)}"
        )

    click.echo(colorify(f"{TICK} Done.", GREEN))
