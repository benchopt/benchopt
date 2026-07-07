import pathlib

import pytest

from benchopt.cli.skills import sync_skills, SKILL_NAME


def _sync(args=()):
    sync_skills(list(args), standalone_mode=False)


def test_packaged_skill_present():
    from benchopt.cli.skills import _source_skill
    assert (_source_skill() / "SKILL.md").is_file()


def test_sync_local(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _sync()

    agents = tmp_path / ".agents" / "skills"
    claude = tmp_path / ".claude" / "skills"
    assert (agents / SKILL_NAME / "SKILL.md").is_file()
    mirror = claude / SKILL_NAME
    assert mirror.exists()
    assert (mirror / "SKILL.md").resolve() == (agents / SKILL_NAME / "SKILL.md").resolve()


def test_sync_into_benchmark_path(tmp_path):
    bench = tmp_path / "my_benchmark"
    bench.mkdir()
    _sync([str(bench)])

    agents = bench / ".agents" / "skills"
    assert (agents / SKILL_NAME / "SKILL.md").is_file()


def test_sync_idempotent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _sync()
    _sync()  # must not raise nor duplicate

    agents = tmp_path / ".agents" / "skills"
    assert (agents / SKILL_NAME / "SKILL.md").is_file()


def test_sync_preserves_unrelated_skills(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _sync()

    agents = tmp_path / ".agents" / "skills"
    repo = agents / "myrepo-local"
    repo.mkdir()
    (repo / "SKILL.md").write_text("local")

    _sync()
    assert (repo / "SKILL.md").is_file()


def test_no_claude_flag(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _sync(["--no-claude"])

    assert (tmp_path / ".agents" / "skills").is_dir()
    assert not (tmp_path / ".claude").exists()



def test_sync_global(tmp_path, monkeypatch):
    monkeypatch.setattr(pathlib.Path, "home", classmethod(
        lambda cls: tmp_path))
    _sync(["--global"])

    agents = tmp_path / ".agents" / "skills"
    assert (agents / SKILL_NAME / "SKILL.md").is_file()


def test_sync_global_with_path_raises(tmp_path):
    from click.exceptions import UsageError
    bench = tmp_path / "my_benchmark"
    bench.mkdir()
    with pytest.raises(UsageError, match="--global"):
        _sync([str(bench), "--global"])
