---
name: benchopt-run-benchmark
description: >
  How to run a benchopt benchmark and manage results: selecting
  objectives/datasets/solvers (with parameter grids), repetitions and budgets,
  parallelism (local and SLURM), conda environments, installing requirements,
  preparing data, caching, and plotting/publishing. Use when running an
  existing benchmark, not when authoring one.
---

# Running a benchopt benchmark

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
  
  Refer to benchopt-parallel skill for more info about parallelism.

## Caching

Each run is cached with joblib; re-running skips already-stored combinations.
The cache invalidates automatically when solver/objective/dataset code changes.

- `-f/--force-solver SOLVER`: force re-running specific solvers.
- `--no-cache`: disable caching for this run.

## Install requirements and prepare data

```bash
benchopt install .              # create/populate the benchmark's conda env
benchopt install . -s my-solver # only what a given solver needs
benchopt install . --env-name myenv --recreate   # rebuild the env
benchopt prepare .              # run Dataset.prepare() (downloads/preprocessing)
```

`benchopt install` only works from a conda environment. `--gpu` selects GPU
requirements; `--minimal` installs just benchopt + objective deps.

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
  
See benchopt-results skill for more info about result management.

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

- Running & scaling: https://benchopt.github.io/user_guide/running.html
- Parallel / cluster runs: https://benchopt.github.io/user_guide/distributed_run.html
- Parametrization & selectors: https://benchopt.github.io/user_guide/class_customization.html#parametrized
- CLI reference: https://benchopt.github.io/user_guide/CLI_ref.html
