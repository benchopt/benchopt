# Running benchopt in parallel

Benchopt parallelises at the granularity of one **(dataset, objective, solver,
repetition) with unique parameters** — each such configuration is an independent
task. There are three backends: `loky` (local, default), `dask`, and `submitit`
(SLURM).

## Local: `--n-jobs`

```bash
benchopt run . -j 4      # 4 local workers via joblib/loky
```

- Default is sequential (`n_jobs=1`). `-j/--n-jobs N` runs N tasks at once.
- joblib caps C-level (BLAS) threads to avoid oversubscription, so an individual
  parallel run can be **slower** than the same run sequentially. Do **not**
  compare wall-times measured under different `-j` values against each other —
  use a sequential run for timing-sensitive comparisons.

## Cluster: `--parallel-config <file.yml>`

A YAML file selects the backend and configures it. The only required key is
`backend`; everything else is backend-specific. `--n-jobs` still applies (it is
injected as `n_jobs` into the config).

```bash
benchopt run . --parallel-config config_parallel.yml
```

### SLURM (`submitit`)

```yaml
# config_parallel.yml
backend: submitit
slurm_time: 01:00:00          # max runtime per job
slurm_gres: gpu:1             # 1 GPU per job
slurm_additional_parameters:
  cpus-per-task: 10
  account: ACC@NAME
```

- Install with `pip install benchopt[submitit]`.
- Each unique configuration is submitted as one job in a **job array**. Logs land
  in `./benchopt_run/` inside the benchmark dir.
- Every `slurm_*` key is forwarded to `submitit.AutoExecutor.update_parameters`,
  so any submitit/SLURM parameter is available.
- By default there is **no cap** on simultaneous jobs; set
  `slurm_array_parallelism: N` to limit concurrency when the scheduler requires it.
- `group_by: dataset|solver|objective` collapses the runs sharing that key into a
  single job, to cut scheduling overhead when there are many configurations.
  `batch_n_jobs: N` then runs each group on N workers inside its job — request
  the matching CPUs (e.g. `slurm_cpus_per_task`) or they oversubscribe. Runs with
  different SLURM configs are never grouped together.

### Dask

```yaml
backend: dask
dask_address: 127.0.0.1:8786   # attach to a running scheduler
```

- Install with `pip install benchopt[dask]`. `dask_*` keys configure the
  `Client`; with no `dask_address`, a local cluster is started with `--n-jobs`
  workers. `coiled_*` keys spin up a Coiled cloud cluster instead.

## Timeout interaction

- `--timeout SECONDS` (or `10m`/`2h`) is the **per-solver** wall-clock budget;
  `--no-timeout` removes it (the two flags are mutually exclusive).
- Under `submitit`, if you do **not** set `slurm_time`, benchopt derives the job's
  SLURM time limit as **1.5 × `--timeout`**, times the number of runs the job
  executes serially when `group_by` batches them. If a solver legitimately runs
  longer than that (slow startup, large data), set `slurm_time` explicitly or the
  scheduler will kill the job before the solver finishes.

## Per-solver and per-run SLURM overrides

The config used for a run is merged in order — **benchmark config < solver
static < run-specific** — so later layers win:

```python
class Solver(BaseSolver):
    name = "gpu-solver"
    # static per-solver override
    slurm_params = {"slurm_partition": "gpu", "slurm_gres": "gpu:1"}
    # per-run override: any `parameters` key prefixed with `slurm_` is swept
    # into the SLURM config for that run
    parameters = {"slurm_nodes": [1, 2]}
```

Runs with different SLURM parameters are dispatched as **separate job arrays**.

## Caching across nodes and machines

- Results are cached with `joblib.Memory` keyed on code + parameters, identically
  to a sequential run. On a cluster this "just works" **only with a shared
  filesystem** across the nodes — otherwise each node caches locally.
- `--collect` reads already-cached results without launching new work (useful to
  build the report while a big array is still running); it forces the local
  `loky` backend regardless of the config.
- To combine results produced on **machines without a shared filesystem**, run
  each separately and `benchopt merge` the parquet outputs (see
  [results.md](./results.md)).

## Stopping a run

- **Local (`loky`/`dask`):** pressing **Ctrl+C** on the main process is
  sufficient — joblib sends the signal to all workers and they exit cleanly.
- **SLURM (`submitit`):** Ctrl+C stops the orchestrator but the already-submitted
  SLURM jobs keep running independently. You must cancel them explicitly:
  ```bash
  scancel <jobid>          # cancel a single job or array
  scancel --user=$USER     # cancel all your pending/running jobs
  ```
  Job IDs are printed when the run starts and are also visible with `squeue -u $USER`.

## Doc links

- Distributed / cluster runs: https://benchopt.github.io/stable/user_guide/distributed_run.html
- CLI reference: https://benchopt.github.io/stable/user_guide/CLI_ref.html
