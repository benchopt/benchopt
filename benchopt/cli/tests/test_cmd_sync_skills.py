import json
import pathlib

from benchopt.cli.skills import sync_skills
from benchopt.cli.skills import _iter_source_skills
from benchopt.cli.skills import MANIFEST_NAME


SKILL_NAMES = sorted(name for name, _ in _iter_source_skills())


def _sync(args=()):
    sync_skills(list(args), standalone_mode=False)


def _manifest(agents_dir):
    with open(agents_dir / MANIFEST_NAME) as f:
        return json.load(f)


def test_packaged_skills_present():
    # Sanity check that skills are shipped and discoverable.
    assert SKILL_NAMES, "no packaged benchopt-* skills found"
    assert "benchopt-create-benchmark" in SKILL_NAMES


def test_sync_local(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _sync()

    agents = tmp_path / ".agents" / "skills"
    claude = tmp_path / ".claude" / "skills"
    for name in SKILL_NAMES:
        assert (agents / name / "SKILL.md").is_file()
        # Claude mirror points back at the canonical copy.
        mirror = claude / name
        assert mirror.exists()
        assert (mirror / "SKILL.md").resolve() == \
            (agents / name / "SKILL.md").resolve()

    manifest = _manifest(agents)
    assert sorted(manifest["skills"]) == SKILL_NAMES
    assert manifest["benchopt_version"]


def test_sync_into_benchmark_path(tmp_path):
    # An explicit benchmark path is used instead of the current directory.
    bench = tmp_path / "my_benchmark"
    bench.mkdir()
    _sync([str(bench)])

    agents = bench / ".agents" / "skills"
    assert sorted(_manifest(agents)["skills"]) == SKILL_NAMES
    for name in SKILL_NAMES:
        assert (agents / name / "SKILL.md").is_file()


def test_sync_idempotent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _sync()
    _sync()  # must not raise nor duplicate

    agents = tmp_path / ".agents" / "skills"
    assert sorted(_manifest(agents)["skills"]) == SKILL_NAMES
    for name in SKILL_NAMES:
        assert (agents / name / "SKILL.md").is_file()


def test_sync_removes_stale_but_keeps_repo_skills(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _sync()

    agents = tmp_path / ".agents" / "skills"
    claude = tmp_path / ".claude" / "skills"

    # Inject a stale benchopt-* skill (as if deleted upstream) ...
    stale = agents / "benchopt-old"
    stale.mkdir()
    (stale / "SKILL.md").write_text("stale")
    (claude / "benchopt-old").symlink_to("../../.agents/skills/benchopt-old")
    manifest = _manifest(agents)
    manifest["skills"].append("benchopt-old")
    (agents / MANIFEST_NAME).write_text(json.dumps(manifest))

    # ... and a repo-specific skill that must be preserved.
    repo = agents / "myrepo-local"
    repo.mkdir()
    (repo / "SKILL.md").write_text("local")

    _sync()

    assert not stale.exists()
    assert not (claude / "benchopt-old").exists()
    assert (repo / "SKILL.md").is_file()
    assert "benchopt-old" not in _manifest(agents)["skills"]


def test_no_claude_flag(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _sync(["--no-claude"])

    assert (tmp_path / ".agents" / "skills").is_dir()
    assert not (tmp_path / ".claude").exists()


def test_dry_run_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _sync(["--dry-run"])

    assert not (tmp_path / ".agents").exists()
    assert not (tmp_path / ".claude").exists()


def test_sync_global(tmp_path, monkeypatch):
    # --global targets ~/.agents/skills; redirect home to a temp dir.
    monkeypatch.setattr(pathlib.Path, "home", classmethod(
        lambda cls: tmp_path))
    _sync(["--global"])

    agents = tmp_path / ".agents" / "skills"
    assert sorted(_manifest(agents)["skills"]) == SKILL_NAMES
    for name in SKILL_NAMES:
        assert (agents / name / "SKILL.md").is_file()
