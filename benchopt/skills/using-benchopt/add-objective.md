# Adding or editing an Objective

Start from the template: [`assets/objective.py`](./assets/objective.py).

The `Objective` is the single file (`objective.py`) that defines what is being
evaluated and how solver outputs are scored. It is the contract every solver and
dataset in the benchmark must satisfy.

## Data flow

```
Dataset.get_data()        → dict → Objective.set_data(**data)
Objective.get_objective() → dict → Solver.set_objective(**obj)
Solver.get_result()       → dict → Objective.evaluate_result(**res)
```

`evaluate_result` returns a dict of metrics; each becomes an `objective_<name>`
column in the result parquet (e.g. `train_loss`, `accuracy`). For **iterative /
convergence** eval, include the scalar key benchopt tracks for progress —
`value` by default, or another key selected via `key_to_monitor` on the stopping
criterion (see below). For **`run_once`** eval there is no required key.

## Parameters

`parameters` is a class variable (dict of name → list of values); benchopt runs
the cartesian product and exposes each selected value as `self.<name>`. Use it to
parametrize the *evaluation* itself (e.g. regularisation strength, number of
scoring steps), not just the solvers and datasets — each combination becomes an
independent entry in the results. Override from the CLI with
`-o "<name>[param=value]"`.

## Requirements and imports (install detection)

Import third-party deps at module top level and let `ImportError` propagate — a
silent `try`/`except` fallback hides a missing dep and causes cryptic runtime
failures. Reserve `safe_import_context` for the rare case of a **class-body
attribute** evaluated at definition time that references an imported name; for
imports only used inside methods a plain top-level import is enough. (numpy is
always available — it ships as a benchopt dependency — so it never needs
guarding.)

## Class customization

### Benchmark-wide defaults

Set these on the `Objective` so **all solvers inherit them** without repeating
per-solver:

- **`sampling_strategy`** — `"run_once"` for fixed-budget / ML benchmarks
  (one call to `run()`); `"iteration"` or `"callback"` for convergence curves.
- **`stopping_criterion`** — override `SufficientProgressCriterion` (the
  default) with `NoCriterion()` for fixed-budget training that must not be
  truncated early. For iterative eval it watches `objective_value` (stops on NaN
  or worsening by > 1e5); monitor another metric by passing `key_to_monitor` to
  the criterion, e.g. `SufficientProgressCriterion(key_to_monitor="train_loss")`
  (the key must appear in `evaluate_result`'s output). See
  [add-solver.md](./add-solver.md) for details.
- **`python_version`** — pins the conda env's Python for `benchopt install`.
- **`min_benchopt_version`** — minimum benchopt release the benchmark requires;
  checked by CI.

### Design: keeping solvers dataset-agnostic

Have the dataset expose a **generic payload** (e.g. `X`, `y`, or
`fields: dict[str, ndarray]`) plus *optional callables* (`moments_fn`, …).
The objective calls the callables only when present; solvers operate on the
payload by name. One set of solvers then works across many datasets without
modification.

### Controlling randomness

For a **stochastic evaluation** (e.g. subsampled scoring), seed from
`self.get_seed(use_repetition=True)` — call it in `set_data` or `get_objective`;
a bare `self.get_seed()` returns the same seed every repetition. Most objectives
are deterministic and need no seeding.

### Optional methods

- **`skip(**data)`**: return `(True, "reason")` to skip incompatible
  dataset/objective combinations before any solver runs.
- **`get_one_result()`**: return a dummy solver result (same shape as
  `get_result()` would produce). Used by `benchopt test` to validate
  `evaluate_result` without running a real solver — omit it and that check is
  skipped.
- **`save_final_results(**res)`**: called after the last `evaluate_result`;
  persist heavy artefacts (models, arrays) as a `.pkl` alongside the parquet.

## Testing

`test_config` (same shape as `parameters`) selects a tiny, fast config and can
name the test dataset (`{'dataset': {'name': 'simulated', 'n_samples': 50}}`);
`test_dataset_name` picks it directly, and `get_one_result()` lets the suite
validate `evaluate_result` without a real solver. See [debug.md](./debug.md) for
what the suite checks.

## Validate

- `benchopt test . --skip-install` to exercise `get_one_result` and the
  dataset→objective→solver chain.
- `benchopt run . -d <small-dataset> -s <solver> -n 3` as a smoke test — pick a
  fast dataset and solver, as a real run can be slow.
- Check `evaluate_result` in isolation via the debug snippet:
  [`assets/debug_snippet.py`](./assets/debug_snippet.py).

## Doc links

- Objective API: https://benchopt.github.io/stable/user_guide/API_ref.html
- Class customisation (parameters, stopping_criterion): https://benchopt.github.io/stable/user_guide/class_customization.html
- Controlling randomness: https://benchopt.github.io/stable/user_guide/controlling_randomness.html
