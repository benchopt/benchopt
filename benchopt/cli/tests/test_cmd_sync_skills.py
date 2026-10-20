import re
import pathlib
import urllib.error
import urllib.request
from pathlib import Path
from importlib import resources

import pytest

from benchopt.cli.skills import sync_skills, SKILL_NAME


def _sync(args=()):
    sync_skills(list(args), standalone_mode=False)


def test_sync_local(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _sync()

    agents = tmp_path / ".agents" / "skills"
    claude = tmp_path / ".claude" / "skills"
    assert (agents / SKILL_NAME / "SKILL.md").is_file()
    mirror = claude / SKILL_NAME
    assert (mirror / "SKILL.md").is_file()
    # mirror is a symlink when supported, a copy otherwise; either way it holds
    # the same content as the agents-dir skill.
    assert (mirror / "SKILL.md").read_text(encoding="utf-8") == (
        agents / SKILL_NAME / "SKILL.md"
    ).read_text(encoding="utf-8")


def test_sync_into_benchmark_path(tmp_path):
    bench = tmp_path / "my_benchmark"
    bench.mkdir()
    _sync([str(bench)])

    agents = bench / ".agents" / "skills"
    assert (agents / SKILL_NAME / "SKILL.md").is_file()
    # nothing leaks into the root temp dir, only under the benchmark path.
    assert not (tmp_path / ".agents").exists()


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
    (repo / "SKILL.md").write_text("local", encoding="utf-8")

    _sync()
    assert (repo / "SKILL.md").read_text(encoding="utf-8") == "local"


def test_no_claude_flag(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _sync(["--no-claude"])

    assert (tmp_path / ".agents" / "skills").is_dir()
    assert not (tmp_path / ".claude").exists()


def test_sync_global(tmp_path, monkeypatch):
    monkeypatch.setattr(pathlib.Path, "home", classmethod(
        lambda cls: tmp_path)
    )
    _sync(["--global"])

    agents = tmp_path / ".agents" / "skills"
    claude = tmp_path / ".claude" / "skills"
    assert (agents / SKILL_NAME / "SKILL.md").is_file()
    assert (claude / SKILL_NAME / "SKILL.md").is_file()


def test_sync_global_with_path_raises(tmp_path):
    from click.exceptions import UsageError
    bench = tmp_path / "my_benchmark"
    bench.mkdir()
    with pytest.raises(UsageError, match="--global"):
        _sync([str(bench), "--global"])


def test_sync_stamps_version(tmp_path, monkeypatch):
    from benchopt import __version__
    from benchopt.cli.skills import VERSION_PLACEHOLDER
    monkeypatch.chdir(tmp_path)
    _sync()

    skill_md = tmp_path / ".agents" / "skills" / SKILL_NAME / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    assert VERSION_PLACEHOLDER not in text
    assert __version__ in text


def test_sync_retargets_doc_version(tmp_path, monkeypatch):
    from benchopt.cli.skills import _doc_url_version
    monkeypatch.chdir(tmp_path)
    _sync()

    skill = tmp_path / ".agents" / "skills" / SKILL_NAME
    texts = "\n".join(
        p.read_text(encoding="utf-8") for p in skill.rglob("*.md")
    )
    # doc links now point at the matching version, not the shipped /stable/.
    assert "benchopt.github.io/stable/" not in texts
    assert f"benchopt.github.io/{_doc_url_version()}/" in texts


# --- Doc links in the packaged skill ---------------------------------------
# Extract http(s) URLs, stopping at whitespace, markdown/quoting delimiters and
# ``<>`` so template placeholders like ``https://github.com/<org>/<bench>`` are
# not picked up as real links.
URL_RE = re.compile(r"https?://[^\s)\"'`<>]+")


def _collect_doc_urls():
    """Return {url: source_file} for benchopt doc links in the skill files."""
    urls = {}
    with resources.as_file(resources.files("benchopt") / "skills") as skills:
        for md in Path(skills).rglob("*.md"):
            for match in URL_RE.finditer(md.read_text(encoding="utf-8")):
                url = match.group(0).rstrip(".,;:")   # trailing sentence punct
                if "benchopt.github.io" in url:
                    urls.setdefault(url, md.name)
    return urls


DOC_URLS = _collect_doc_urls()


def _url_status(url):
    """HTTP status for ``url`` (drops ``#anchor``); GET if HEAD refused."""
    target = url.split("#", 1)[0]
    headers = {"User-Agent": "benchopt-tests"}
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(target, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (403, 405, 501):
                continue   # some servers refuse HEAD; retry with GET
            return e.code
    return None


def test_skill_has_doc_urls():
    # Guard against the regex silently matching nothing (e.g. skill moved).
    assert DOC_URLS, "no benchopt.github.io links found in the packaged skill"


@pytest.mark.network
@pytest.mark.parametrize("url", sorted(DOC_URLS))
def test_skill_doc_url_valid(url):
    try:
        status = _url_status(url)
    except urllib.error.URLError as e:
        pytest.skip(f"no network access: {e.reason}")
    assert status is not None and status < 400, (
        f"{url} (in {DOC_URLS[url]}) returned HTTP {status}"
    )
