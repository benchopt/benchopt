# Adding or editing an Objective

Start from the template: [`assets/objective.py`](./assets/objective.py).

The `Objective` is the single file (`objective.py`) that defines what is being
minimised and how solver outputs are scored. It is the contract every solver and
dataset in the benchmark must satisfy.

## Data flow

```
Dataset.get_data()        → dict → Objective.set_data(**data)
Objective.get_objective() → dict → Solver.set_objective(**obj)
Solver.get_result()       → dict → Objective.evaluate_result(**res)
```

`evaluate_result` must return a dict with at least a scalar **`value`** key —
the quantity benchopt minimises for convergence curves. Add any extra metric
keys you like (e.g. `train_loss`, `accuracy`); each becomes an
`objective_<name>` column in the result parquet.

## Optional methods

- **`get_one_result()`**: return a dummy solver result (same shape as
  `get_result()` would produce). Used by `benchopt test` to validate
  `evaluate_result` without running a real solver — omit it and that check is
  skipped.
- **`save_final_results(**res)`**: called after the last `evaluate_result`;
  persist heavy artefacts (models, arrays) as a `.pkl` alongside the parquet.
- **`skip(**data)`**: return `(True, "reason")` to skip incompatible
  dataset/objective combinations before any solver runs.

## Benchmark-wide defaults

Set these on the `Objective` so **all solvers inherit them** without repeating
per-solver:

- **`sampling_strategy`** — `"run_once"` for fixed-budget / ML benchmarks
  (one call to `run()`); `"iteration"` or `"callback"` for convergence curves.
- **`stopping_criterion`** — override `SufficientProgressCriterion` (the
  default) with `NoCriterion()` for fixed-budget training that must not be
  truncated early. See [add-solver.md](./add-solver.md) for details.
- **`python_version`** — pins the conda env's Python for `benchopt install`.
- **`min_benchopt_version`** — minimum benchopt release the benchmark requires;
  checked by CI.

## Controlling which metric drives convergence detection

By default benchopt watches `objective_value` for divergence (NaN or worsening
by > 1e5). To watch a different metric, set:

```python
key_to_monitor = "objective_train_loss"   # must be a key in evaluate_result's output
```

## Parametrising evaluation

Use `Objective.parameters` to parametrize the *evaluation* itself (e.g.
regularisation strength, number of scoring steps), not just the solvers and
datasets. Each combination becomes an independent entry in the results.

## Design: keeping solvers dataset-agnostic

Have the dataset expose a **generic payload** (e.g. `X`, `y`, or
`fields: dict[str, ndarray]`) plus *optional callables* (`moments_fn`, …).
The objective calls the callables only when present; solvers operate on the
payload by name. One set of solvers then works across many datasets without
modification.

## Requirements and imports

Use `safe_import_context` only for class-body attributes evaluated at definition
time that reference an imported name. For regular imports, let `ImportError`
propagate — a silent fallback hides missing deps and causes cryptic runtime
failures.

```python
from benchopt import BaseObjective, safe_import_context

with safe_import_context() as import_ctx:
    import numpy as np   # only needed at class-body definition time
```

For imports only used inside methods, import at module top level without
`safe_import_context`.

## Testing

- Set `test_dataset_name` to select the dataset used by `benchopt test`
  (defaults to the first discovered dataset).
- Add `test_config` on the `Objective` for fast test parameters (same shape as
  `parameters`).
- Implement `get_one_result()` so `benchopt test` validates `evaluate_result`.

## Validate

- `benchopt run . -d Simulated -s <any-solver> -n 3` as a smoke test.
- `benchopt test . --skip-install` to exercise `get_one_result` and the
  dataset→objective→solver chain.
- Check `evaluate_result` in isolation via the debug snippet:
  [`assets/debug_snippet.py`](./assets/debug_snippet.py).

## Doc links

- Objective API: https://benchopt.github.io/stable/user_guide/API_ref.html
- Class customisation (parameters, stopping_criterion): https://benchopt.github.io/stable/user_guide/class_customization.html
- Controlling randomness: https://benchopt.github.io/stable/user_guide/controlling_randomness.html
