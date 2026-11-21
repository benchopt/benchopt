# Adding a solver

Start from the template: [`assets/solver.py`](./assets/solver.py).

A solver lives in `solvers/<name>.py` as `class Solver(BaseSolver)` and must
work against the benchmark's existing `Objective`. After each change, run
`benchopt test . --skip-install` for the design checks and a quick
`benchopt run . -s <name> -d <small-dataset> -n 5` smoke test.

## Data flow

- `set_objective(**objective_dict)` receives `Objective.get_objective()`'s output.
- `get_result()` returns a dict unpacked into `Objective.evaluate_result(**res)`.

## Parameters

`parameters` is a class variable (dict of name → list of values); benchopt runs
the cartesian product and exposes each selected value as `self.<name>`. Override
from the CLI with `-s "<name>[param=value]"`.

## Requirements and imports (install detection)

benchopt decides a solver is installed by **importing the module and catching
`ImportError`**, so:

- **Import third-party deps at module top level** — never function-locally and
  never in a `try`/`except` fallback; let `ImportError` propagate. A silent
  fallback makes benchopt mark the solver *installed*, then fail cryptically at
  run time. This applies to imported `benchmark_utils` helpers too.
- Set `requirements` to exactly what the solver needs (`["pip::pkg"]` for pip,
  `["chan::pkg"]` for a conda channel) as a **literal list of strings** —
  benchopt reads it statically via `ast`, so a computed value
  (`OtherSolver.requirements + [...]`) is not parsable.
- Avoid `safe_import_context` except for class-body attributes that reference an
  imported name at definition time.

## Class customization

### sampling_strategy — how the computation budget is varied

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
instead — it drives exactly `N` callback calls (or one `run(N)`). A single run
is recorded as `run_once`, and `SingleRunCriterion` only accepts the
`run_once` and `callback` strategies (`iteration` is the same as `run_once`).

When *every* solver in the benchmark is fixed-budget (e.g. a DL benchmark where
all solvers train for N epochs), set `stopping_criterion` **once on the
`Objective`** rather than repeating it per solver — like `sampling_strategy`, a
solver that doesn't define its own inherits the objective's, so this makes the
no-truncation behavior benchmark-wide. A solver with `sampling_strategy =
"run_once"` still runs once, whatever the objective's criterion. The early-truncation symptom is covered
in [debug.md](./debug.md).

### Controlling randomness

For **stochastic** solvers, seed from `self.get_seed(use_repetition=True)` (call
it in `set_objective`) so `--n-repetitions N` gives N genuinely different but
reproducible runs; a bare `self.get_seed()` returns the same seed every
repetition. Add `use_dataset=True` / `use_solver=True` to further differentiate seeds.

### Checkpointing a long training

Store the state of a training in `self.get_checkpoint_path()`: this directory
is the same from one `benchopt run` to the next, so `run` can load a checkpoint
if it exists and resume or skip the training. Do not rebuild such a path from
`get_run_output_path()`, which changes at each run. It needs no guard: with
`--checkpoint off`, it is a temporary directory.

```python
def run(self, _):
    checkpoint = self.get_checkpoint_path() / "checkpoint.pt"
    self.model = fit(self.X, self.y, checkpoint=checkpoint)  # load or train
```

The directory depends on the seed, the repetition, the code of the dataset and
solver files, and the parameters of the three components. List the parameters
that only change the evaluation in `eval_parameters = ("n_eval", ...)`, on the
`Dataset`, `Objective` or `Solver` defining them: runs that differ only by
them share one training. The objective code is not in the key, so a new metric
is computed from the existing checkpoints. benchopt does not check any of
this: after a change of training code outside the solver file, run with
`--checkpoint refresh` to remove the checkpoints and train again. Write files
atomically (temporary name, then `os.replace`).

In a parallel run, runs sharing a training start together and each one trains.
Run `benchopt run --no-eval` first (one run per training), then the full
`benchopt run`, which evaluates the other runs from the checkpoints.

With `sampling_strategy = "callback"`, do not write the files yourself: give
the checkpoint to the callback and restart from `self.checkpoint_` (`None` on
a fresh start). benchopt stores it with the callback state (iteration, time),
at each evaluation and every 10 minutes, so a restarted run gives the same
curve.

```python
def run(self, callback):
    model, optimizer = build(self.X)
    if self.checkpoint_ is not None:
        model.load_state_dict(self.checkpoint_["model"])
        optimizer.load_state_dict(self.checkpoint_["optimizer"])

    def checkpoint():  # only called when benchopt stores it
        return dict(model=model.state_dict(),
                    optimizer=optimizer.state_dict())

    while callback(checkpoint=checkpoint):
        train_one_step(model, optimizer)
```

- Put everything needed to continue in the checkpoint (optimizer, schedule,
  step counter, RNG state), and keep it picklable.
- Call the callback **before** the first step (`while callback(...)`): points
  are re-evaluated by calling `run` with `checkpoint_` set and stopping it at
  its first callback call.
- `--checkpoint rescore` evaluates all the stored points again without
  training, e.g. after adding a metric. Without it, stored evaluations are
  reused, with a warning if the objective code changed.
- `checkpoint_keep = k` (solver, or objective for all solvers) keeps only the
  `k` last points. Default keeps all, which `rescore` needs for a full curve.
- `checkpoint_interval = seconds` (same places, default 600) sets how often
  the checkpoint is stored between two evaluations.

### Optional methods

- `skip(self) -> str | None`: declare incompatibility with
  a given problem (e.g. needs a feature the objective doesn't expose). Return
  the reason to skip, or `None`/no return to run; any other value raises. It
  is checked before launching the run. Prefer parameters (`objective.reg`):
  `objective.get_objective()` works but loads the data on the machine running
  `benchopt run`. The old `skip(**objective_dict)` and the `(skip, reason)`
  tuple are deprecated. For a GPU check, use
  `benchopt.helpers.requires_gpu.gpu_available(self)`, not the local CUDA: the
  front node may lack the GPU of the SLURM jobs.
- `warm_up()`: called once before timed runs; call `self.run_once()` here to
  absorb JIT/compilation costs out of the timings.
- `pre_run_hook(stop_val)`: untimed per-run setup (e.g. JAX precompilation for
  a given iteration count).
- `get_next(stop_val)`: override the default logarithmic `stop_val` schedule.
  Define it on the `Objective` to change it for all solvers.

## Testing

`test_config` (a flat dict of single values, not a grid) selects a tiny, fast
config so `benchopt test` runs quickly; it can also carry `dataset`/`objective`
keys to pick fast test data (including the dataset name). See
[debug.md](./debug.md) for what the suite checks.

## Validate

- `benchopt run . -s <name> -d <small-dataset> -n 5` as a smoke test.
- `benchopt test . -k <Solver>` to exercise `test_config` (skip the
  `*_install` test with `--skip-install` if your env cannot build isolated envs or
  to avoid long env creation).
- `flake8 .` or `ruff check .` on the changed file.

## Doc links

- Iterative solvers & sampling: https://benchopt.github.io/stable/user_guide/iterative_solvers.html
- Class config (parameters, requirements, hooks): https://benchopt.github.io/stable/user_guide/class_customization.html
- Controlling randomness: https://benchopt.github.io/stable/user_guide/controlling_randomness.html
- Solver languages (R, Julia, CLI, …): https://benchopt.github.io/stable/user_guide/solver_languages.html
- API reference: https://benchopt.github.io/stable/user_guide/API_ref.html
