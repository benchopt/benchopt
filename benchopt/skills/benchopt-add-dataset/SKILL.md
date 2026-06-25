---
name: benchopt-add-dataset
description: >
  How to add a dataset to an existing benchopt benchmark: the Dataset class
  contract (get_data feeding Objective.set_data), parameters, requirements,
  expensive one-time prepare() with caching, reproducible seeding, a
  zero-dependency Simulated dataset, and test_parameters. Use when implementing
  or fixing a dataset, not when authoring a whole benchmark.
---

# Adding a dataset

A dataset lives in `datasets/<name>.py` as `class Dataset(BaseDataset)` and
must produce data the benchmark's `Objective` can consume. Smoke-test with
`benchopt run . -d <name> -s <solver> -n 5`.

## The contract

```python
from benchopt import BaseDataset

class Dataset(BaseDataset):
    name = "simulated"
    parameters = {"n_samples": [100, 1000], "n_features": [20, 50]}
    requirements = []   # zero-dependency datasets are great smoke tests

    def get_data(self):
        rng = np.random.default_rng(self.get_seed(use_repetition=True))
        X = rng.standard_normal((self.n_samples, self.n_features))
        y = X @ rng.standard_normal(self.n_features)
        return dict(X=X, y=y)   # -> Objective.set_data(**data)
```

- `get_data()` **must return a dict**; benchopt calls
  `Objective.set_data(**data)` with it.
- Selected parameter values are available as `self.n_samples`, etc., and the
  cartesian product of `parameters` is instantiated automatically.
- Keep the payload **generic** so many solvers can consume it; expose optional
  callables (e.g. `moments_fn`) the objective uses when present, rather than
  baking solver-specific assumptions into the data.

## Reproducible randomness

Call `self.get_seed(use_repetition=True)` to obtain a deterministic seed that
changes with the repetition index, so `--n-repetitions N` yields N genuinely
different draws. A bare `self.get_seed()` returns the same seed for every
repetition.

## Expensive one-time work: prepare()

For downloads/extraction/heavy preprocessing, put the work in `prepare()`
(cached by joblib, triggered by `benchopt prepare`), and have `get_data()` load
the prepared artefacts:

```python
prepare_cache_ignore = ("seed",)   # params that don't affect prepare()

def prepare(self):
    # idempotent; safe to call repeatedly
    download_and_preprocess(self._cache_path)
```

- `prepare()` must be **idempotent**. List params that don't affect its output
  in `prepare_cache_ignore` (or `"all"` to run at most once per class).
- Since `benchopt run` never calls `prepare()` (it runs only via the dedicated
  `benchopt prepare`, or `benchopt install --prepare`), share an idempotent
  `_ensure_prepared()` between `prepare()` and `get_data()` so the dataset also
  works on a fresh checkout without an explicit prepare step.

## Requirements and imports (install detection)

benchopt detects installation by **importing the module and catching
`ImportError`**:

- **Import third-party deps at module top level**, never function-locally.
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
- Ship at least one zero-dependency `Simulated` dataset so the benchmark always
  has a no-install smoke test.

## test_parameters

Add a `test_parameters` dict (same shape as `parameters`) pointing at a tiny,
fast configuration so `benchopt test` runs in seconds on a fresh checkout.

## Validate

- `benchopt run . -d <name> -s <solver> -n 5` as a smoke test.
- `benchopt test . -k <Dataset>` to exercise `test_parameters`.
- `flake8 .` or `ruff check .` on the changed file.

## Doc links

- Class config (parameters, requirements, prepare, hooks): https://benchopt.github.io/user_guide/class_customization.html
- Controlling randomness: https://benchopt.github.io/user_guide/controlling_randomness.html
- API reference: https://benchopt.github.io/user_guide/API_ref.html
