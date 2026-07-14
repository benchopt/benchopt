# Running a benchopt benchmark

Run config template: [`assets/config_run.yml`](./assets/config_run.yml).
SLURM parallel config: [`assets/config_parallel_slurm.yml`](./assets/config_parallel_slurm.yml).

Runs on the provided benchmark, defaulting to the current folder (`.`, the
directory holding `objective.py`).

## Select what to run

```bash
benchopt run . \
    -o "objective[reg=0.1]" \
    -d "simulated[n_samples=100,n_features=[20,50]]" \
    -s my-solver
```

- `-o/--objective`, `-d/--dataset`, `-s/--solver` filter by **name** (repeatable).
  Omit a filter to run all of that kind.
- Override parameters inline with `name[param=value]`. Values use Python literal
  syntax: `reg=0.1`, `use_acceleration=True`, lists `n_features=[20,50]`, and
  grouped params `'n_samples, n_features'=[(100,20),(1000,50)]`. Only the
  parameters you name are replaced; the rest keep their class defaults, and the
  cartesian product is taken over the remainder.
- Repeat a component with different parameters to run a **union** of grids
  instead of one full cartesian product — each entry expands independently:
  `-s "my-solver[lr=[0.1,0.01]]" -s "my-solver[lr=1.0,momentum=[0.5,0.9]]"`.
- Keep long selections in a config file instead of the CLI — see
  [Run configuration file](#run-configuration-file) below.

## Budgets and repetitions

- `-r/--n-repetitions N`: independent repetitions with potentially different
  seeds for error bars or more reliable time estimates.
- `-n/--max-runs N`: max number of points sampled along each convergence curve.
  Iterative eval only — ignored for `run_once` solvers.
- `--timeout SECONDS` / `--no-timeout`: per-solver wall-clock budget. Also
  iterative eval only, and only checked at each evaluation, so it is not a hard
  cap (see [debug.md](./debug.md)).

## Parallelism and environments

- `-j/--n-jobs N`: N local workers (sequential by default).
- `--parallel-config slurm.yml`: dispatch on a cluster (SLURM, Dask, …).
- `-e/--env [NAME]` / `--env-name NAME`: run inside a dedicated conda env
  (isolated dependencies). `-l/--local` (default) runs in the current env.

See [parallel.md](./parallel.md) for full parallelism and cluster options.

## Caching

Each run is cached with joblib; re-running skips already-stored combinations.
The cache invalidates automatically when solver/objective/dataset code changes.

- `-f/--force-solver SOLVER`: force re-running specific solvers.
- `--no-cache`: disable caching for this run.

### Long runs, interruptions, and resuming

benchopt caches every finished `(dataset, objective, solver, params,
repetition)` cell, so a long run does **not** need manual chunking:

- **Crash / Ctrl-C**: completed cells are already cached. Re-running the exact
  same command picks up where it left off — cached cells are skipped, only the
  missing ones run.
- **Consolidate partial results without computing**: re-issue the *same* command
  with `--collect` appended. It only reads the cache and writes the parquet for
  what is done, so it is safe to run repeatedly mid-run (e.g. from another shell)
  to inspect progress.
- **Resume**: re-run the same command *without* `--collect` (cached cells
  skipped, missing ones computed).

Gotchas that break cache matching or surprise you:

- `--output` takes a **name**, not a path (results always land in `outputs/`).
- `-o` is the **objective** filter, not output.
- Keep `-s`/`-d`/params **identical** across runs — any change alters the cache
  keys, so cells won't be recognised as already done.

## Install requirements and prepare data

### First-time setup

```bash
git clone https://github.com/<org>/<benchmark> && cd <benchmark>
benchopt install .                       # install all solver/dataset deps into the current env
benchopt prepare .                       # download/preprocess datasets (runs Dataset.prepare())
benchopt run . -d Simulated -s my-solver # smoke test
```

By default `benchopt install` installs into the **current Python environment**.
To use an isolated conda env instead use `-e` (benchmark's default env name,
derived from `objective.py`) or `--env-name NAME` (custom name):

```bash
benchopt install . -e                    # install into the benchmark's default conda env
benchopt run . -e -s my-solver           # run inside that same env

benchopt install . --env-name bench_env  # install into a named conda env
benchopt run . --env-name bench_env -s my-solver
```

`--env-name` also works with a **pre-existing conda env** (e.g. a carefully
pinned GPU env on a shared machine): it adds only the selected components'
requirements there — always prefer it over installing deps manually with pip.

Gotcha: the install check imports each requirement by name from the benchmark
directory, so a local folder can **shadow** a pip package and fool it — e.g.
the benchmark's `datasets/` folder shadows the HF `datasets` library, making
benchopt report it "already available" while it is missing. Verify with an
import from *outside* the benchmark dir when in doubt.

### Selective install

```bash
benchopt install . -s my-solver             # only deps for one solver
benchopt install . -d my-dataset            # only deps for one dataset
benchopt install . --env-name myenv --recreate   # rebuild the conda env from scratch
benchopt install . --gpu                    # select GPU-variant requirements
benchopt install . --minimal                # benchopt + objective only (no solvers)
```

### Check what is installed

```bash
benchopt info .             # list solvers/datasets and their install status
benchopt info . -e          # check availability inside the benchmark conda env
benchopt info . -s my-solver -v   # verbose: parameters + requirements
```

### Prepare datasets

```bash
benchopt prepare .              # run Dataset.prepare() for all datasets
benchopt prepare . -d my-dataset  # one dataset only
```

`prepare` is idempotent and safe to re-run. Use it to download large files or
run expensive preprocessing once before any benchmarking run.

## Results, plots, sharing

- Results are `.parquet` files under `./outputs/`. An HTML dashboard is
  generated unless `--no-html`; `--no-plot`/`--no-display` skip plotting.
- The name of the output can be controlled with the `--output` option.
  If the name already exist, the new result is postfixed with `-1` or
  `-X` the X-th time.
- `benchopt plot <result.parquet>` regenerates figures; custom plots are
  configured via a config file (`plot_configs:` with `plot_kind`, `scale`).
- `benchopt merge` combines results from different machines/users;
  `benchopt publish` shares on GitHub or Hugging Face.

See [results.md](./results.md) for full result management.

## Run configuration file

Instead of long CLI lines, pass `--config config.yml`. CLI option names become
top-level keys, and `objective:`/`dataset:`/`solver:` take the same selectors —
either the inline `name[param=value]` string, or a **nested dict** of parameters
(clearer when a component has many params):

```yaml
n-repetitions: 3
max-runs: 30
dataset:
  - "simulated[n_samples=[100,1000]]"    # inline string form
solver:
  - my-solver:                            # nested-dict form
      lr: [0.1, 0.01]                     # each key is a parameter
      momentum: 0.9
```

List the same component more than once to run a **union** of grids rather than
one full cartesian product — each entry expands on its own:

```yaml
solver:
  - my-solver:
      lr: [0.1, 0.01]
      momentum: 0.9
  - my-solver:
      lr: 1.0
      momentum: [0.5, 0.99]
```

**Preview a config without running it** — add `--collect`:
`benchopt run . --config config.yml --collect` enumerates every selected
configuration and reports its cache status (missing ones show as `not run yet`),
without launching any solver — the quickest way to confirm the run matrix is
what you expect.

## Useful extras

- `--seed N`: fix the base seed for reproducibility.
- `--profile`: profile solvers (line-level timing).
- `--pdb`: drop into a debugger on error.
- `--output NAME`: name the output files.

## Doc links

- Running & scaling: https://benchopt.github.io/stable/user_guide/running.html
- Parallel / cluster runs: https://benchopt.github.io/stable/user_guide/distributed_run.html
- Parametrization & selectors: https://benchopt.github.io/stable/user_guide/class_customization.html#parametrized
- CLI reference: https://benchopt.github.io/stable/user_guide/CLI_ref.html
