# Adding a dataset

Start from the template: [`assets/dataset.py`](./assets/dataset.py).

A dataset lives in `datasets/<name>.py` as `class Dataset(BaseDataset)` and
must produce data the benchmark's `Objective` can consume. After each change,
run `benchopt test . --skip-install` for the design checks and a quick
`benchopt run . -d <name> -s <solver> -n 5` smoke test.

## Parameters

`parameters` is a class variable: a dict mapping names to lists of values.
Benchopt takes the cartesian product, so each combination is a distinct dataset
instance, with the selected values exposed as `self.<name>`:

```python
class Dataset(BaseDataset):
    parameters = {"n_samples": [100, 1000], "n_features": [20]}
```

Override from the CLI with `-d "<name>[n_samples=500]"`. Point `benchopt test`
at a small, fast combination via `test_parameters` (see below).

## Data flow and design

`get_data()` must return a dict; benchopt calls `Objective.set_data(**data)` with it.
Keep the payload **generic** — expose optional callables (e.g. `moments_fn`) the
objective uses when present, rather than baking solver-specific assumptions into the data.

Use `self.get_seed(use_repetition=True)` so `--n-repetitions N` yields N genuinely
different draws; a bare `self.get_seed()` returns the same seed every repetition.
Add `use_dataset=True` to also vary the seed across datasets, so different
datasets don't share the same draw.

## Locating data files: get_data_path()

Use `get_data_path()` (from `benchopt.config`) instead of hardcoding paths
relative to `__file__`. It returns `<benchmark>/data/` by default and respects
`data_home` / `data_paths` overrides in `benchopt.cfg`, so users can point at
an existing data store without touching the code:

```python
from benchopt.config import get_data_path

def get_data(self):
    path = get_data_path() / f"{self.dataset_name}.pkl"
    ...
```

With a named key (`get_data_path("my_dataset")`), the path can be individually
overridden in `benchopt.cfg`:
```ini
[benchmark]
data_paths = {"my_dataset": "/scratch/datasets/my_dataset"}
```

## Expensive one-time work: prepare()

For downloads/extraction/heavy preprocessing, put the work in `prepare()`
(cached by joblib) and have `get_data()` only load the already-prepared
artefacts. `prepare()` is triggered by `benchopt prepare .`; `benchopt run` does **not**
call it.

**Per-dataset download pattern** — ideally each `Dataset` instance downloads
only the files it needs, not all files at once:

```python
from benchopt.config import get_data_path

def prepare(self) -> None:
    dest = get_data_path() / f"{self.dataset_name}.pkl"
    if dest.exists():
        return                          # idempotent
    dest.parent.mkdir(parents=True, exist_ok=True)
    _download(self.dataset_name, dest)  # fetch only this file
```

Then `benchopt prepare . -d "MyDataset[dataset_name=taxi]"` fetches only
`taxi.pkl`. Running without `-d` prepares every parameter combination.

- `prepare()` must be **idempotent**. List params that don't affect its output
  in the `prepare_cache_ignore` class variable (or set it to `"all"` to run at
  most once per class).
- Since bare `benchopt run` skips `prepare()`, share an idempotent
  `_ensure_prepared()` guard between `prepare()` and `get_data()` if you want
  the dataset to self-heal on first use without an explicit prepare step.

## Requirements and imports (install detection)

benchopt detects installation by **importing the module and catching
`ImportError`**:

- **Import third-party deps at module top level**, never function-locally.
  This also applies to shared `benchmark_utils` helper modules the dataset
  imports — a lazy import there hides the dep from the install check just
  the same.
- **Never wrap an import in `try`/`except` with a fallback.** A silent fallback
  lets the module import even when the dep is missing, so benchopt marks the
  dataset *installed* and the failure resurfaces — cryptically — at run time.
  Let `ImportError` propagate.
- Set `requirements` to exactly what this dataset needs (`["pip::pkg"]`,
  `["chan::pkg"]`).
- **Keep `requirements` a literal list of strings** — benchopt reads it
  *statically* (via `ast`, without importing the module), so a computed value
  like `requirements = OtherDataset.requirements + ["pip::extra"]` is not
  parsable.
- Avoid `safe_import_context` except for class-body attributes evaluated at
  definition time that reference an imported name (e.g. a subclass referencing a
  parent's imported symbols).
- Ship a zero-dependency `Simulated` dataset when possible so the benchmark always
  has a no-install smoke test. Put `Simulated` in its own file
  (`datasets/simulated.py`). **This matters especially if the real dataset has
  heavy deps** (e.g. torch for loading pickles): sharing a file would pull in the
  heavy dep even for the smoke test, defeating the purpose.

## test_parameters

Add a `test_parameters` dict (same shape as `parameters`) pointing at a tiny,
fast configuration so `benchopt test` runs in seconds on a fresh checkout.

## Validate

- `benchopt test . -k <Dataset>` to exercise `test_parameters` (fast design
  checks; add `--skip-install` if your env can't build isolated envs).
- `benchopt run . -d <name> -s <solver> -n 5` as a smoke test — pick a fast
  solver, as a real run can be slow.
- `flake8 .` or `ruff check .` on the changed file.

## Doc links

- Class config (parameters, requirements, prepare, hooks): https://benchopt.github.io/stable/user_guide/class_customization.html
- Controlling randomness: https://benchopt.github.io/stable/user_guide/controlling_randomness.html
- API reference: https://benchopt.github.io/stable/user_guide/API_ref.html
