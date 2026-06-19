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
change: `benchopt run . -s <name> -d <small-dataset> -n 5`.

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
dropout, …), seed from `self.get_seed()` rather than a fixed literal or an
unseeded global RNG. The seed changes with the repetition index, so
`--n-repetitions N` gives N genuinely different — but reproducible — runs:

```python
def run(self, n_iter):
    rng = np.random.default_rng(self.get_seed())
    w = rng.standard_normal(self.n_features)   # reproducible random init
    ...
```

## sampling_strategy — how the curve is sampled

Set `sampling_strategy` on the solver (or default it at the `Objective` level):

- `"run_once"`: `run` is called exactly once, no convergence curve (typical for
  ML). Often set once on the `Objective` so all solvers inherit it.
- `"iteration"`: `run(stop_val)` is called repeatedly with an increasing
  integer number of iterations (default logarithmic schedule).
- `"tolerance"`: `stop_val` is a decreasing float tolerance.
- `"callback"`: `run(callback)` receives a callable; call it once per
  iteration — it records time/objective and returns `False` when to stop:
  ```python
  def run(self, callback):
      while callback():
          self.w_ -= self.step_size * grad(self.w_)
  ```

`stopping_criterion` (an instance like `SufficientProgressCriterion` or
`NoCriterion`) controls when iterative runs stop; defaults are derived from the
sampling strategy. See the doc links.

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

Add a `test_parameters` dict (same shape as `parameters`) pointing at a tiny,
fast configuration so `benchopt test` exercises the solver quickly.

## Validate

- `benchopt run . -s <name> -d <small-dataset> -n 5` as a smoke test.
- `benchopt test . -k <Solver>` to exercise `test_parameters` (skip the
  `*_install` test if your env cannot build isolated envs).
- `flake8 .` or `ruff check .` on the changed file.

## Doc links

- Iterative solvers & sampling: https://benchopt.github.io/user_guide/iterative_solvers.html
- Class config (parameters, requirements, hooks): https://benchopt.github.io/user_guide/class_customization.html
- Solver languages (R, Julia, CLI, …): https://benchopt.github.io/user_guide/solver_languages.html
- API reference: https://benchopt.github.io/user_guide/API_ref.html
