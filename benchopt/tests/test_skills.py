"""Checks on the packaged agent skill shipped under ``benchopt/skills``."""
import re
import urllib.error
import urllib.request
from pathlib import Path
from importlib import resources

import pytest


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
    """HTTP status for ``url`` (drops any ``#anchor``); GET if HEAD is refused."""
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
