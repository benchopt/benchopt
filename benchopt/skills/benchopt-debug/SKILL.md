---
name: benchopt-debug
description: >
  How to drive a benchmark's code directly from Python via the Benchmark
  object, without launching the full `benchopt run` CLI: load datasets and the
  objective, inspect what `Dataset.get_data()` returns, replay a solver
  (`set_objective`/`run`/`get_result`) and call `Objective.evaluate_result()` on
  its output or an arbitrary checkpoint. Covers common pitfalls — NaNs, diverging
  curves (benchopt's divergence guard), and stale-cache surprises plus how to bust
  the cache — and points to `benchopt test` for catching design problems early.
  Use when debugging a benchmark's own code (a failing `get_data`, a diverging
  solver, NaNs, a suspicious metric, results that don't update after an edit) rather
  than running or authoring one.
---

# Debugging a benchopt benchmark from Python

When something in a benchmark misbehaves, you usually do not want a full
`benchopt run`: caching, conda envs, parallel workers and the convergence loop
all sit between you and the line that breaks. The `Benchmark` object lets you
load and call the exact same classes the runner uses, in a plain interpreter,
so you can step through `get_data`, `set_data` and `evaluate_result` directly.

Run these snippets from the benchmark directory (the folder holding
`objective.py`), e.g. `python -i debug.py` or a notebook.

## Load the benchmark

```python
from benchopt.benchmark import Benchmark

bench = Benchmark(".")                       # path to the benchmark dir
```

This discovers `objective.py`, `datasets/` and `solvers/` the same way the CLI
does, so the classes you get back behave identically to a real run.

## Inspect a dataset and its data

`get_datasets()` returns the Dataset **classes** (not instances). Instantiate
one with its parameters, then call `get_data()`:

```python
datasets = bench.get_datasets()             # list of Dataset classes
Dataset = next(d for d in datasets if d.name == "my-dataset")

dataset = Dataset.get_instance(n_samples=100)   # apply parameters
data = dataset.get_data()                        # the dict passed to the objective
print(type(data), data.keys())
```

`get_instance(**params)` is the canonical constructor (it applies the class
`parameters` grid); use it instead of calling `Dataset()` yourself. The dict
returned by `get_data()` is exactly what the runner forwards to
`Objective.set_data(**data)`, so inspecting it here tells you what every solver
will actually receive.

## Inspect the objective and replay evaluate_result

```python
Objective = bench.get_benchmark_objective()  # the Objective class
objective = Objective.get_instance()         # add params if the objective takes any

objective.set_data(**data)                   # same data dict as above
```

`evaluate_result(**solver_result)` takes the keys that the benchmark's
`Solver.get_result()` returns — so the argument names are benchmark-specific
(commonly `beta=`, or `model=`/`dist=` for model-training benchmarks). Pass a
result you constructed yourself to exercise the metric code in isolation:

```python
metrics = objective.evaluate_result(model=my_model, dist=None)
print(metrics)                               # dict of objective values
```

If you only want the parameters a solver would receive, call
`objective.get_objective()` — that is the dict handed to
`Solver.set_objective(**...)`.

## Debug a solver

`get_solvers()` returns the Solver **classes**. You can drive the full solver
lifecycle by hand, which is the quickest way to find out *why* a solver
diverges, is skipped, or returns a malformed result — without the convergence
loop, caching or parallel workers around it:

```python
Solver = next(s for s in bench.get_solvers() if s.name == "my-solver")
solver = Solver.get_instance(lr=1e-3)        # apply solver parameters

obj_dict = objective.get_objective()         # what the runner passes to the solver

# Optional: solvers can opt out of an objective/dataset combination.
skip, reason = solver.skip(**obj_dict)
print("skipped" if skip else "runs", reason)

solver.set_objective(**obj_dict)             # hand the objective to the solver
solver.run(10)                               # run to a stopping value (see below)
result = solver.get_result()                 # dict of quantities to evaluate
```

The meaning of `run`'s argument depends on `sampling_strategy`
(`'iteration'` → integer steps, `'tolerance'` → a tolerance, `'callback'` →
the solver calls a callback itself, `'run_once'` → runs a single time). For a
fast smoke test, `solver.run_once()` runs the solver exactly once. Then feed the
output straight into the metric code from the previous section:

```python
print(objective.evaluate_result(**result))  # close the solver → objective loop
```

This is the minimal reproduction of one point on a convergence curve. If
`evaluate_result(**result)` raises or returns nonsense, the mismatch is between
the keys in `get_result()` and the arguments `evaluate_result` expects — print
both to compare.

## Gotcha: the `datasets/` directory can be shadowed

In a plain script, `import datasets` (or anything that triggers it) may resolve
to Hugging Face's `datasets` package instead of the benchmark's local
`datasets/` folder, or vice-versa, depending on `sys.path`. **Do not import the
benchmark's modules by hand** — always go through `Benchmark(".")`, which loads
each dataset/objective from its file path and sidesteps the name clash
entirely.

## Worked example: an eval oracle

A common use is validating the *evaluation* path on its own: load a known model
(e.g. a saved checkpoint) and confirm the objective reports what you expect,
without training anything.

```python
from benchopt.benchmark import Benchmark

bench = Benchmark(".")

# 1. Get the data the objective evaluates against.
Dataset = next(d for d in bench.get_datasets() if d.name == "fineweb")
data = Dataset.get_instance().get_data()

# 2. Some benchmarks expose a reference/oracle model through get_data();
#    otherwise load your own checkpoint here.
oracle_model = data["model"]                 # or torch.load("ckpt.pt"), etc.

# 3. Run the real metric code on it.
objective = bench.get_benchmark_objective().get_instance()
objective.set_data(**data)
print(objective.evaluate_result(model=oracle_model, dist=None))
```

If this prints sensible metrics, the eval path is sound and any weird curve in a
full run points at the *solvers*, not the objective.

## Common pitfalls and how to pin them

### Diverging curves and NaNs

For sequential solvers that are evaluated with varying compute budget,
benchopt watches the monitored objective (`key_to_monitor`, default
`objective_value`) and **stops the run with status `diverged`** as soon as that
value is `NaN` or worsens by more than `1e5` between two steps
([stopping_criterion.py](../stopping_criterion.py)). A curve that ends early with
`diverged` in the dashboard is this guard firing, not a benchopt bug.

Both symptoms almost always originate in your code, so reproduce them with the
replay snippets above instead of staring at the curve:

- **NaN / inf in the metric.** Run `objective.evaluate_result(**result)` on the
  solver's output (or a hand-built one) and check each returned value with
  `np.isfinite`. NaNs usually come from the metric itself (`log(0)`, divide-by-
  zero, an empty slice) — isolate it here, with no solver in the loop.
- **Solver blow-up.** Drive `solver.run(...)` step by step and print the iterate
  norm; an exploding norm points at the step size / learning rate or a missing
  normalization, not the objective.
- **Watching the wrong key.** If divergence detection seems to trigger on the
  wrong quantity, make sure `key_to_monitor` names the metric you intend (it must
  be a key returned by `evaluate_result`).

### Stale-cache surprises

`benchopt run` caches each `(solver, dataset, rep)` with `joblib.Memory`, keyed on
the **function source + parameters**. Editing a solver's own `.py` invalidates its
cache automatically — but changes that don't alter that function's source do
**not**, so you can silently get old numbers after:

- editing an **imported helper module** (the solver source is unchanged),
- changing a **data file** or external resource `get_data()` reads,
- upgrading a **dependency** that changes results.

If a result looks wrong or "didn't update after my edit", bust the cache:

```bash
benchopt run . -f my-solver        # force re-run of one solver (-f repeatable)
benchopt run . --no-cache          # ignore the cache entirely for this run
```

The `Benchmark(".")` workflow in this skill bypasses the cache completely, so
re-deriving a suspicious value here and comparing it to the run is itself the
quickest way to confirm the cache was stale.

## Catch design problems early with the test suite

Before (or instead of) hand-driving classes, `benchopt test .` runs benchopt's
built-in benchmark test suite against your code. It exercises the same contracts
as the snippets above and fails loudly on the design mistakes that are painful
to discover during a full run:

```bash
benchopt test .                       # full suite in a temporary env
benchopt test . -k my-solver          # pytest args pass through (scope the run)
benchopt test . --env-name myenv      # reuse/inspect a named conda env
```

What the suite checks (so you know which failure points where):

- `test_dataset_class` / `test_dataset_get_data` — each Dataset instantiates and
  `get_data()` returns a well-formed dict.
- `test_benchmark_objective` — `set_data` + `evaluate_result` run on the
  designated **test dataset** and the objective returns the expected metrics.
- `test_benchmark_config_validity` — the benchmark's test config is coherent.
- `test_solver_class`, `test_solver_stopping_criterion`, `test_solver_run` —
  each Solver instantiates, respects its `sampling_strategy` / stopping
  criterion, and actually runs on the test dataset.

Point the objective/solver tests at a small, fast case: set the objective's
`test_dataset_name` to select the dataset used for testing, and use the
`test_config` class attribute (on Dataset/Objective/Solver) to pass cheap test
parameters. This keeps the suite fast to re-run while iterating on early design
choices. See the test configuration reference:
https://benchopt.github.io/benchmark_workflow/test_benchmark.html

## Tips

- For an error *inside* a real run, `benchopt run . --pdb` drops into the
  debugger at the failing line — reach for the Benchmark object when you want to
  reproduce or probe the code outside the run loop.
- Everything here uses the installed benchmark code in the current environment;
  no conda env, caching or parallelism is involved, so edits to the benchmark's
  `.py` files take effect on the next `Benchmark(".")` / re-import.

## Doc links

- Benchmark structure & workflow: https://benchopt.github.io/benchmark_workflow/index.html
- Objective / Dataset / Solver API: https://benchopt.github.io/user_guide/API_ref.html
- Class customization & parameters: https://benchopt.github.io/user_guide/class_customization.html
- Testing a benchmark (test_config): https://benchopt.github.io/benchmark_workflow/test_benchmark.html
