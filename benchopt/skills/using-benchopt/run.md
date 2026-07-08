# Running a benchopt benchmark

Run config template: [`assets/config_run.yml`](./assets/config_run.yml).
SLURM parallel config: [`assets/config_parallel_slurm.yml`](./assets/config_parallel_slurm.yml).

Run from a benchmark directory (the folder holding `objective.py`). `.` refers
to the current benchmark.

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

## Budgets and repetitions

- `-n/--max-runs N`: max number of points sampled along each convergence curve.
  Only used for benchmark which evaluate iterative methods over time.
- `-r/--n-repetitions N`: independent repetitions with potentially different seeds for
  error bars or to have more reliable time estimates.
- `--timeout SECONDS` / `--no-timeout`: per-solver wall-clock budget.

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
top-level keys, and `objective:`/`dataset:`/`solver:` take the same selectors:

```yaml
n-repetitions: 3
max-runs: 30
dataset:
  - "simulated[n_samples=[100,1000]]"
solver:
  - my-solver
```

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
