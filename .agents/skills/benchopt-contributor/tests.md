# Writing Tests For benchopt

## Workflow

1. Read the implementation file(s) being tested.
2. Read at least one neighbouring test file — patterns are intentionally
   consistent. CLI-command tests live in `benchopt/cli/tests/` as
   `test_cmd_<command>.py` (e.g. `test_cmd_run.py`, `test_cmd_test.py`,
   `test_cmd_merge.py`, `test_cmd_publish.py`); add a new command's tests there.
3. Produce a **draft** of the full test file or the new test method(s).
4. Review and refine the draft against the conventions below; keep this skill
   updated as patterns evolve.

## Core Utilities

```python
from benchopt.utils.temp_benchmark import temp_benchmark  # real benchmark in a tmpdir
from benchopt.tests.utils import CaptureCmdOutput         # captures stdout/stderr + result files
from benchopt.tests.utils import patch_import, patch_var_env
```

Invoke CLI functions directly — never via subprocess unless testing the module entry point:

```python
from benchopt.cli.main import run
from benchopt.cli.process_results import publish, merge, plot

run([str(bench.benchmark_dir), "-d", "test-dataset", "--no-plot", "-n", "1"],
    "benchopt", standalone_mode=False)
```

Pass args as a **list** (not `.split()`) when any argument is dynamic or may contain spaces.

## `temp_benchmark`

The universal fixture. Accepts strings, lists of strings, or `{filename: source}` dicts. Default datasets/solvers are injected when None is passed or when using a dict. Extra files can be set in any place of the temporary benchmark, e.g. to add a `test_config.py` or `config.yml` file: 

```python
with temp_benchmark() as bench:                          # all defaults
with temp_benchmark(solvers=solver_src) as bench:        # custom solver string
with temp_benchmark(
    datasets=[ds1_src, ds2_src],
    solvers={"named_solver.py": solver_src},
    config={"config.yml": {"solver": [...]}},
    extra_files={"test_config.py": check_src},
) as bench:
    ...
```

Use `bench.benchmark_dir` when passing to CLI commands.

Components are passed as indented source strings — `temp_benchmark` runs
`inspect.cleandoc`, so any consistent indentation works:

```python
solver = """
    from benchopt import BaseSolver
    class Solver(BaseSolver):
        name = "my-solver"
        def set_objective(self, X, y, lmbd): pass
        def run(self, _): pass
        def get_result(self): return dict(beta=None)
"""
with temp_benchmark(solvers=solver) as bench: ...
```

## `CaptureCmdOutput`

```python
with CaptureCmdOutput() as out:                          # deletes result files after
    run([...], standalone_mode=False)
out.check_output("pattern")                              # at least one match
out.check_output("pattern", repetition=N)                # exactly N matches

with CaptureCmdOutput(delete_result_files=False) as out: # keep files for later use
    ...
result_file = Path(out.result_files[0])

with CaptureCmdOutput(exit=1) as out:                    # expect SystemExit(1)
    ...
```

`check_output` strips ANSI colour codes and uses `re.findall`.

## Class Structure

**Configuration-independent tests go in a base class** (shared across hubs,
backends, …). Subclasses add `setup_class` and the configuration-specific
tests:

```python
class TestCmdFoo:
    """Tests shared across all configurations."""

    def _make_result_file(self, bench): ...   # shared helper

    @pytest.mark.parametrize("hub", ["github", "huggingface"])
    def test_missing_package(self, monkeypatch, hub): ...

class TestCmdFooGitHub(TestCmdFoo):
    def setup_class(cls):
        pytest.importorskip("github", reason="PyGithub required")

    def _setup_mock(self, mock_cls): ...      # subclass-specific helper
```

Use **`setup_class`** (not `setup`) for `pytest.importorskip` — it runs once per class,
not once per test method.

Use **`setup_class` / `teardown_class`** when expensive state (running the benchmark,
generating result files) should be created once and shared across all tests in the class,
as in `TestPlotCmd` and `TestGenerateResultCmd`.

## Parametrize Style

- **Flat single-value parametrize** with internal `if/else` for configuration-dependent logic,
  rather than tuple parametrize with many parameters:

```python
# Preferred
@pytest.mark.parametrize("hub", ["github", "huggingface"])
def test_missing_package(self, monkeypatch, hub):
    if hub == "github":
        pkg, module = "github", GH_MODULE
    else:
        pkg, module = "huggingface_hub", HF_MODULE

# Avoid
@pytest.mark.parametrize("hub, pkg, module, match, extra_args", [...])
```

- Use **string values as IDs directly** to avoid a separate `ids=` list:

```python
@pytest.mark.parametrize("token", ["no_token", "invalid_token"])
# rather than: @pytest.mark.parametrize("token", [None, "bad"], ids=["no_token", ...])
```

- Keep **structurally different cases as separate tests** even when they look symmetric —
  e.g. "no token" (error raised before any API call) vs "invalid token" (error from inside
  the API call) call different code paths and need different mocks.

## Error Path Tests

```python
with pytest.raises(click.BadParameter, match=re.escape(msg)):
    cmd([...], standalone_mode=False)

with pytest.raises(RuntimeError, match="Could not find"):
    publish([...], standalone_mode=False)

with CaptureCmdOutput(exit=1) as out:      # for SystemExit rather than exceptions
    run([...], standalone_mode=False)
out.check_output("FAILED", repetition=2)
```

## Mocking External APIs

**Patch at the usage site** (`benchopt.results.<hub>.*`), not the origin module:

```python
GH_MODULE = "benchopt.results.github"
HF_MODULE = "benchopt.results.hugging_face"

@patch(f"{HF_MODULE}.HfApi")
@patch(f"{HF_MODULE}.hf_hub_download")
def test_...(self, mock_hf_download, mock_hf_api_cls): ...  # reversed from decorator order
```

Extract multi-level mock wiring into a `_setup_<hub>_mock` helper to avoid repeating
it in every test:

```python
def _setup_github_mock(self, mock_Github, username="testuser"):
    mock_g = MagicMock()
    mock_Github.return_value = mock_g
    mock_g.get_user.return_value.login = username
    mock_origin = MagicMock()
    mock_g.get_repo.return_value = mock_origin
    mock_fork = MagicMock()
    mock_origin.create_fork.return_value = mock_fork
    mock_fork.get_branch.return_value = MagicMock()   # branch exists by default
    return mock_g, mock_origin, mock_fork
```

**`side_effect` patterns:**
- Single exception instance → raised on every call.
- List of values/exceptions → consumed in order (for sequential calls with different
  outcomes; exception instances in the list are raised, other values are returned).

**Exception constructors** — use the real signature to avoid errors:

```python
RepositoryNotFoundError("msg", response=MagicMock(status_code=404))
GithubException(404, {"message": "Not Found"})
```

## Simulating a Missing Package

Block the underlying package via `monkeypatch` so the module's `try/except ImportError`
guard re-runs and surfaces its friendly error message:

```python
import sys  # at the top of the file, not inside the test

def test_missing_package(self, monkeypatch, hub):
    monkeypatch.delitem(sys.modules, hub_module, raising=False)  # force re-import
    monkeypatch.setitem(sys.modules, pkg, None)                  # block dep import
    with pytest.raises(ImportError, match="<pkg> package is required"):
        publish([...], standalone_mode=False)
```

`monkeypatch` restores `sys.modules` automatically after the test.

When simulating missing requirements, you can also use the dummy_package, that
can be specified in the `requirements` from `from benchopt.tests.fixtures import DUMMY_PACKAGE_REQ` and to make sure it is not present before the test, use the `uninstall_dummy_package` fixture.

## Result File Assertions

When a test needs to inspect the DataFrame:

```python
from benchopt.results import read_results

with CaptureCmdOutput(delete_result_files=False) as out:
    run([...], standalone_mode=False)
df = read_results(Path(out.result_files[0]))
assert len(df) == expected_rows
assert df["run_date"].nunique() == 2
```

## Before declaring a draft done

Verify against the conventions detailed above — the recurring ones:
base class for config-independent tests, single-value `parametrize` with
internal `if/else`, `setup_class` for `importorskip`, string parametrize IDs,
separate tests for structurally different error paths, real exception
signatures, `import sys` at file top. Sharp edges are collected in
[gotchas](./gotchas.md).
