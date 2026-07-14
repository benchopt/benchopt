# Adding a dataset

Start from the template: [`assets/dataset.py`](./assets/dataset.py).

A dataset lives in `datasets/<name>.py` as `class Dataset(BaseDataset)` and
must produce data the benchmark's `Objective` can consume. After each change,
run `benchopt test . --skip-install` for the design checks and a quick
`benchopt run . -d <name> -s <solver> -n 5` smoke test.

## Data flow

`get_data()` must return a dict; benchopt calls `Objective.set_data(**data)` with it.
Keep the payload **generic** — expose optional callables (e.g. `moments_fn`) the
objective uses when present, rather than baking solver-specific assumptions into the data.

## Parameters

`parameters` is a class variable (dict of name → list of values); benchopt runs
the cartesian product — each combination is a distinct dataset instance — and
exposes each selected value as `self.<name>`. Override from the CLI with
`-d "<name>[param=value]"`.

## Requirements and imports (install detection)

benchopt decides a dataset is installed by **importing the module and catching
`ImportError`**, so:

- **Import third-party deps at module top level** — never function-locally and
  never in a `try`/`except` fallback; let `ImportError` propagate. A silent
  fallback makes benchopt mark the dataset *installed*, then fail cryptically at
  run time. This applies to imported `benchmark_utils` helpers too.
- Set `requirements` to exactly what the dataset needs (`["pip::pkg"]`,
  `["chan::pkg"]`) as a **literal list of strings** — benchopt reads it
  statically via `ast`, so a computed value (`OtherDataset.requirements + [...]`)
  is not parsable.
- Avoid `safe_import_context` except for class-body attributes that reference an
  imported name at definition time.
- Ship a zero-dependency `Simulated` dataset in its own file
  (`datasets/simulated.py`) so there is always a no-install smoke test —
  important when the real dataset has heavy deps (e.g. torch), since sharing a
  file would pull them in even for the smoke test.

## Class customization

### Locating data files: get_data_path()

Use `get_data_path()` (from `benchopt.config`) instead of hardcoding paths
relative to `__file__`. It returns `<benchmark>/data/` by default and respects
`data_home` / `data_paths` overrides in `benchopt.cfg`, so users can point at an
existing data store without touching the code:

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

### Controlling randomness

For **stochastic** data generation, seed from `self.get_seed(use_repetition=True)`
(call it in `get_data`) so `--n-repetitions N` yields N genuinely different draws;
a bare `self.get_seed()` returns the same seed every repetition. Add
`use_dataset=True` to also vary the seed across datasets, so different datasets
don't share the same draw.

### Optional methods

`prepare()` — expensive one-time setup (downloads, extraction, heavy
preprocessing), cached by joblib and triggered only by `benchopt prepare .`
(`benchopt run` does **not** call it); `get_data()` then just loads the prepared
artefacts. Ideally each `Dataset` instance downloads only the files it needs:

```python
from benchopt.config import get_data_path

def prepare(self) -> None:
    dest = get_data_path() / f"{self.dataset_name}.pkl"
    if dest.exists():
        return                          # idempotent
    dest.parent.mkdir(parents=True, exist_ok=True)
    _download(self.dataset_name, dest)  # fetch only this file
```

- `prepare()` must be **idempotent**; list params that don't affect its output in
  `prepare_cache_ignore` (or set it to `"all"` to run at most once per class).
- Since bare `benchopt run` skips `prepare()`, share an idempotent
  `_ensure_prepared()` guard between `prepare()` and `get_data()` if you want the
  dataset to self-heal on first use without an explicit prepare step.

## Testing

`test_parameters` (same shape as `parameters`) selects a tiny, fast config so
`benchopt test` runs quickly. See [debug.md](./debug.md) for what the suite
checks.

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
