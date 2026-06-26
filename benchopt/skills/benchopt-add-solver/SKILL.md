---
name: benchopt-add-solver
description: >
  How to add a solver to an existing benchopt benchmark: the Solver class
  contract (set_objective/run/get_result), sampling strategies and stopping
  criteria for convergence curves, parameters, requirements, skipping
  incompatible problems, warm-up/JIT handling, and test_parameters. Use when
  implementing or fixing a solver, not when authoring a whole benchmark.
---

# Adding a solver

A solver lives in `solvers/<name>.py` as `class Solver(BaseSolver)` and must
work against the benchmark's existing `Objective`. Run a smoke test after each
change: `benchopt run . -s <name> -d <small-dataset> -n 5` with a small dataset.

## The contract

```python
from benchopt import BaseSolver

class Solver(BaseSolver):
    name = "my-solver"
    parameters = {"step_size": [0.1, 1.0]}   # swept as a cartesian product
    requirements = ["numpy", "pip::some-pkg"]

    def set_objective(self, **objective_dict):
        # objective_dict is exactly Objective.get_objective()'s output.
        # Store what you need on self.
        ...

    def run(self, stop_val):
        # Do the work for the given budget. Do NOT return the result here.
        ...

    def get_result(self):
        # Return a dict whose keys match Objective.evaluate_result's args.
        return {"beta": self.beta_}
```

- `set_objective(**objective_dict)` ← `Objective.get_objective()`.
- `get_result()` → dict → `Objective.evaluate_result(**res)`.
- Access selected parameters as `self.step_size`, etc.

## Reproducible randomness

For **stochastic** solvers (random initialization, mini-batch shuffling,
dropout, …), seed from `self.get_seed(use_repetition=True)` rather than a fixed
literal or an unseeded global RNG. With `use_repetition=True` the seed changes
with the repetition index, so `--n-repetitions N` gives N genuinely different —
but reproducible — runs (a bare `self.get_seed()` returns the same seed for
every repetition):

```python
def run(self, n_iter):
    rng = np.random.default_rng(self.get_seed(use_repetition=True))
    w = rng.standard_normal(self.n_features)   # reproducible random init
    ...
```

Note that if the seed need to be different for each dataset/solver, you can use `use_dataset=True` and/or `use_solver=True` in `get_seed()`.

## sampling_strategy — how the computation budget is varied

Set `sampling_strategy` on the solver (or default it at the `Objective` level):

- `"run_once"`: `run` is called exactly once, no convergence curve (typical for
  ML). Often set once on the `Objective` so all solvers inherit it.
- `"iteration"`: `run(stop_val)` is called repeatedly with an increasing
  integer number of iterations (default logarithmic schedule), starting from scratch each time.
- `"tolerance"`: `stop_val` is a decreasing float tolerance.
- `"callback"`: `run(callback)` receives a callable; call it once per
  iteration — it records time/objective and returns `False` when to stop:
  ```python
  def run(self, callback):
      while callback():
          self.w_ -= self.step_size * grad(self.w_)
  ```

`stopping_criterion` (an instance like `SufficientProgressCriterion` or
`NoCriterion`) controls when iterative runs stop; the default is
`SufficientProgressCriterion(patience=3)`, derived from the sampling strategy.

**Fixed-budget gotcha (DL / fixed-epoch training).** The default stops a run as
soon as the monitored objective fails to improve for `patience=3` successive
evaluations (`eps=1e-10`). On a convergence benchmark that is the point — but
for **fixed-budget training** (run N epochs/steps no matter what) a noisy or
plateauing loss trips it *silently*: the curve ends well before your budget and
the run looks "done". Pin an explicit criterion that does not truncate on
progress:

```python
from benchopt.stopping_criterion import NoCriterion

class Solver(BaseSolver):
    sampling_strategy = "callback"          # or "iteration"
    stopping_criterion = NoCriterion()      # run to --max-runs / timeout, no early stop
```

`NoCriterion` never stops on lack of progress, so the run length is set by
`--max-runs` / `--timeout` (or by your own `run` loop). If `run` already loops
over the whole budget in a single call, use `SingleRunCriterion(stop_val=N)`
instead — it drives exactly `N` callback calls (or one `run(N)`).

When *every* solver in the benchmark is fixed-budget (e.g. a DL benchmark where
all solvers train for N epochs), set `stopping_criterion` **once on the
`Objective`** rather than repeating it per solver — like `sampling_strategy`, a
solver that doesn't define its own inherits the objective's, so this makes the
no-truncation behavior benchmark-wide. See the doc links; the early-truncation
*symptom* is covered in the `benchopt-debug` skill.

## Optional hooks

- `skip(**objective_dict) -> (skip: bool, reason: str | None)`: declare
  incompatibility with a given problem (e.g. needs a feature the objective
  doesn't expose). Return `(True, "why")` to skip, `(False, None)` otherwise.
- `warm_up()`: called once before timed runs; call `self.run_once()` here to
  absorb JIT/compilation costs out of the timings.
- `pre_run_hook(stop_val)`: untimed per-run setup (e.g. JAX precompilation for
  a given iteration count).
- `get_next(stop_val)`: override the default logarithmic `stop_val` schedule.

## Requirements and imports (install detection)

benchopt detects whether a solver is installed by **importing the module and
catching `ImportError`**. Therefore:

- **Import third-party deps at module top level** — never hide them in
  function-local imports.
- **Never wrap an import in `try`/`except` with a fallback.** A silent fallback
  lets the module import even when the dep is missing, so benchopt marks the
  solver *installed* and the failure resurfaces — cryptically — at run time. Let
  `ImportError` propagate.
- Set `requirements` to exactly what this solver needs
  (`["pip::pkg"]` for pip, `["chan::pkg"]` for a conda channel).
- **Keep `requirements` a literal list of strings** — benchopt reads it
  *statically* (via `ast`, without importing the module), so a computed value
  like `requirements = OtherSolver.requirements + ["pip::extra"]` is not
  parsable.
- Do **not** use `safe_import_context` except for class-body attributes
  evaluated at definition time that reference an imported name (e.g. a subclass
  referencing a parent's imported symbols).

## test_parameters

Add a `test_config` dict (same shape as `parameters`) pointing at a tiny,
fast configuration so `benchopt test` exercises the solver quickly.
This config can also have optional `dataset` and `objective` keys,
pointing to dict to specify test parameters for datasets and objective,
including the dataset name to select a given class.

## Validate

- `benchopt run . -s <name> -d <small-dataset> -n 5` as a smoke test.
- `benchopt test . -k <Solver>` to exercise `test_config` (skip the
  `*_install` test with `--skip-install` if your env cannot build isolated envs or
  to avoid long env creation).
- `flake8 .` or `ruff check .` on the changed file.

## Doc links

- Iterative solvers & sampling: https://benchopt.github.io/user_guide/iterative_solvers.html
- Class config (parameters, requirements, hooks): https://benchopt.github.io/user_guide/class_customization.html
- Solver languages (R, Julia, CLI, …): https://benchopt.github.io/user_guide/solver_languages.html
- API reference: https://benchopt.github.io/user_guide/API_ref.html
