# Gotchas — sharp edges you'll get wrong from memory

The traps that pass local checks but fail CI, or silently test nothing. Each
headline is stated once here; the fuller context lives in the linked file.

## Validation

- **`flake8` lints the whole repo, not your file.** CI runs `flake8 .`, so a
  clean diff can still fail on an unrelated violation. Lint the repo, not just
  what you touched. Also: 79-col limit (E501), and `flake8` is **not** in the
  base env — `uv pip install flake8` first. → [general](./general.md)
- **Rebuild docs with `-E`.** Without it Sphinx serves a stale cache and you
  "verify" the old page. `sphinx-build -E -b html doc doc/_build/html`.
  → [docs](./docs.md)

## Tests

- **Patch at the *usage* site, not the origin module** — `@patch("benchopt.results.github.Github")`, not `@patch("github.Github")`. Patching the origin has no effect on the already-imported reference. → [tests](./tests.md)
- **Mock args arrive in *reversed* decorator order.** Bottom-most `@patch` maps
  to the first mock argument. → [tests](./tests.md)
- **Use `setup_class`, not `setup`, for `importorskip` and expensive shared
  state** — `setup` re-runs per test method; `setup_class` runs once per class.
  → [tests](./tests.md)
- **Give exception constructors their real signature** —
  `GithubException(404, {"message": "Not Found"})`,
  `RepositoryNotFoundError("msg", response=MagicMock(status_code=404))`. A
  wrong signature raises inside the test setup, not the code under test.
  → [tests](./tests.md)
- **To simulate a missing package, force the re-import** —
  `monkeypatch.delitem(sys.modules, hub_module, raising=False)` then
  `monkeypatch.setitem(sys.modules, pkg, None)`, so the module's
  `try/except ImportError` guard re-runs. Put `import sys` at the file top.
  → [tests](./tests.md)
- **Pass CLI args as a list, not `.split()`,** when any argument is dynamic or
  may contain spaces. → [tests](./tests.md)
