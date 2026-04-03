# Specification: Dataset Preparation Step Enhancement

## Overview
Add a dedicated `prepare()` step to the `BaseDataset` class to enable efficient, cacheable, and parallelizable dataset preparation. This replaces the current `--download` flag mechanism with a more flexible and robust approach suitable for parallel execution.

---

## Goals
1. **Separation of Concerns**: Separate dataset preparation (download,
   extraction, preprocessing) from data loading (`get_data()`)
2. **Backward Compatibility**: Maintain existing `get_data()` behavior;
   `prepare()` is optional
3. **CLI Support**: Provide a dedicated `benchopt prepare` command to replace 
   `benchopt install --download`
4. **Caching**: Make preparation results easily cacheable to avoid redundant
   computation
5. **Parallelization**: Support parallel execution across multiple datasets, 
   using benchopt parallel_backends

---

## Design

### 1. BaseDataset Class Enhancement

#### New Optional Method: `prepare()`
```python
def prepare(self):
    """Prepare the dataset for use.
    
    This method is called once before any benchmark runs to perform
    expensive operations such as:
    - Downloading data from remote sources
    - Extracting archives
    - Creating cached versions of data
    - Pre-processing or validation
    
    This method:
    - Can be called independently of get_data()
    - Is cached based on dataset parameters
    - Is suitable for parallel execution (no shared state assumed)
    - Is not timed as part of the benchmark
    
    Notes
    -----
    - If not implemented, defaults to no-op
    - Should use dataset parameters declared in `parameters = {...}`
      to determine cache location/behavior.
    - If some dataset parameters do not impact preparation, they should be
      declared in `prepare_cache_ignore` so cache keys and job creation
      ignore them. Use `prepare_cache_ignore = "all"` to ignore all parameters.
    - Should be idempotent: calling it multiple times should be safe
    - Can raise exceptions if preparation fails; these will stop execution
    
    Raises
    ------
    Exception
        Any exception raised here will halt execution and should be
        appropriately logged for debugging on SLURM.
    """
    pass
```

#### Execution Flow
1. When a benchmark is loaded, `prepare()` is called for each dataset instance
2. Cache keying is derived by benchmark cache internals (joblib),
   from function code/signature and inputs
3. Preparation is cached: subsequent calls with same parameters skip execution
4. `get_data()` can assume preparation has been completed

#### Optional Class Attribute: `prepare_cache_ignore`
```python
class Dataset(BaseDataset):
    parameters = {
        "random_state": [0, 1, 2],
        "n_samples": [1000, 10000],
    }

    # parameters that do not affect prepare() outputs
    # use "all" to ignore every parameter (prepare is fully parameter-independent)
    prepare_cache_ignore = ("random_state", "n_samples")
```

Semantics:
- Parameters listed in `prepare_cache_ignore` are ignored in prepare cache keying.
- They are also ignored when creating the parallel prepare job list.
- This avoids duplicated jobs for parameterizations that share the same prepared artifacts.
- The special value `"all"` ignores all parameters, so preparation runs at most once per dataset class regardless of parameterization.

#### Cache Location
- Dataset preparation should use benchmark cache API directly (`benchmark.cache(...)`).
- Cache storage and location are delegated to existing benchmark cache settings.
- This keeps prepare caching centralized with all other BenchOpt cached artifacts.
- No ad-hoc marker files are needed when cached calls are source of truth.

---

### 2. CLI Command: `benchopt prepare`

#### Command Definition
```
benchopt prepare [OPTIONS] BENCHMARK
```

#### Options (coherent with `benchopt run`)
```
-d, --dataset <dataset_name>
    Prepare specific datasets. Can be used multiple times.
    Syntax: dataset_name or dataset_name[param=value]
    Default: all datasets (same behavior as `benchopt run`)

--config <config_file>
    YAML configuration file specifying which datasets to prepare
    (same key format as `benchopt run --config`)

-j, --n-jobs <int>
    Maximal number of workers for local parallel preparation.
    Same meaning as in `benchopt run -j`.

--parallel-config <parallel_config.yml>
    Backend configuration file for distributed or advanced parallel runs.
    Same interface as `benchopt run --parallel-config`.
    Supported backends: `loky`, `dask`, `submitit`.

--timeout <timeout>
    Timeout per dataset preparation job.
    Same parsing rules as in `benchopt run` (`10`, `10m`, `2h`, etc.).

--force
    Force re-preparation even if cached.

--env, -e
    Run preparation in a benchmark-dedicated conda environment
    (`benchopt_<BENCHMARK>`), coherent with `benchopt run --env`.

--env-name <env_name>
    Conda environment to use for preparation
    coherent with `benchopt run --env-name`.
```

#### Usage Examples
```bash
# Prepare all datasets in current environment
benchopt prepare path/to/benchmark

# Prepare with local parallelism (same as run -j)
benchopt prepare path/to/benchmark -j 8

# Prepare with specific dataset and specific parameters
benchopt prepare path/to/benchmark -d "dataset1[param=value]"

# Force re-preparation
benchopt prepare path/to/benchmark --force

# Prepare with distributed backend (same interface as run --parallel-config)
benchopt prepare path/to/benchmark --parallel-config slurm_config.yml

# Prepare with config file + local parallel workers
benchopt prepare path/to/benchmark --config config.yml
```

#### Output Behavior
- Progress bar for each dataset (if not quiet)
- Log level: INFO for progress, WARNING for recoverable issues, ERROR for failures
- Sample output:
  ```
  Preparing datasets for benchmark 'lasso'
  
  [1/3] dataset1 ... OK (cached)
  [2/3] dataset2 ... OK (prepared in 2.3s)
  [3/3] dataset3 ... FAILED: Connection error
  
  Summary: 2/3 datasets ready, 1 failed
  ```

---

### 3. Integration with `benchopt install`

#### Modifications
1. Add a new `--prepare` flag to `benchopt install`.
2. Keep `--download` for backward compatibility, but mark it deprecated.
3. Add deprecation warning when `--download` is used:
   ```
   "The --download flag is deprecated. Use '--prepare' with 'benchopt install' or use 'benchopt prepare'."
   ```
4. `--download` and `--prepare` trigger the same preparation workflow.
5. Preparation call is done in CLI flow (in `benchopt.cli.main.install`), not in `Benchmark.install_all_requirements`.
6. For backward compatibility, if a dataset does not define `prepare`, fallback behavior is to call `get_data`.

#### Updated Behavior
```python
def install(..., download=False, prepare=False, ...):
    # install requirements first
    exit_code = benchmark.install_all_requirements(...)

    # deprecated alias
    if download:
        warnings.warn("--download is deprecated, use --prepare", DeprecationWarning)
    prepare |= download

    if prepare:
        # Call prepare after requirements are installed (CLI-level orchestration)
        exit_code = max(
            exit_code,
            benchmark.prepare_all_data(
                include_datasets,
                env_name=env_name,
                n_jobs=n_jobs,
                parallel_config=parallel_config,
            )
        )

    return exit_code
```

```python
def _prepare_dataset_cached(dataset_cls, dataset_params, prepare_kwargs):
    dataset = dataset_cls(**dataset_params)
    # Backward compatibility fallback
    if hasattr(dataset, "prepare") and callable(dataset.prepare):
        dataset.prepare(**prepare_kwargs)
    else:
        dataset.get_data()
    return True
```

```python
def install_all_requirements(...):
    # ... existing code ...
    # does NOT trigger data preparation; CLI handles it explicitly
    return exit_code
```

---

### 4. Benchmark Class Methods

#### New method: `prepare_all_data()`
```python
def prepare_all_data(self, datasets, env_name=None, n_jobs=None,
                     parallel_config=None, timeout=None, force=False):
    """Prepare all specified datasets.
    
    Parameters
    ----------
    datasets : list of BaseDataset classes
        Datasets to prepare
    env_name : str or None
        Conda environment to use
    n_jobs : int or None
        Local parallelism level (same semantics as run -j)
    parallel_config : dict or None
        Backend configuration as produced by
        `check_parallel_config(parallel_config_file, n_jobs)`
        from `benchopt.parallel_backends`
    timeout : int|float|None
        Timeout per preparation task
    force : bool
        Force re-preparation

    Returns
    -------
    exit_code : int
        0 if all successful, non-zero if any failed
    """
```

1. Reuse `benchopt.parallel_backends.check_parallel_config(...)` to parse backend config.
2. Build dataset parameter products.
3. For each dataset class, collapse parameterizations that only differ on
    `prepare_cache_ignore`.
4. Create one task per unique non-ignored parameter combination.
5. Execute tasks through `benchopt.parallel_backends.parallel_run(...)`.
6. Each task calls a benchmark-cached dataset preparation function.
7. Return summary and non-zero exit code if any task failed.
---

### 5. Dataset Caching & Invalidation
#### Cache Invalidation
1. **Parameter-based**: Cache key includes dataset parameters except those in `prepare_cache_ignore`
2. **Manual override**: `--force` clears dataset-prepare cache entries
3. **Code/version-aware**: joblib invalidates cache when function code/signature changes

#### Ignoring Parameters in Cache
Use benchmark cache `ignore=` to exclude parameters that do not affect preparation outputs.

Example:
```python
class MyDataset(BaseDataset):
    parameters = {
        "n_samples": [1000, 10000],
        "random_state": [0, 1, 2],
    }

    # `random_state` does not affect downloaded/prepared artifacts.
    prepare_cache_ignore = ("random_state",)
    
    def prepare(self):
        # Download and preparation logic
        ...
```

To ignore all parameters (e.g. preparation only downloads a fixed file regardless of any parameter):
```python
    prepare_cache_ignore = "all"
```

#### Cache Wrapper (via benchmark API)
```python
def _prepare_dataset(dataset_cls, dataset_params, ignored_params):
    """Pure preparation function used through benchmark cache."""
    all_params = {**dataset_params, **ignored_params}
    dataset = dataset_cls.get_instance(**all_params)
    if type(dataset).prepare is not BaseDataset.prepare:
        dataset.prepare()
    else:
        dataset.get_data()  # backward-compat fallback
    return True

cached_prepare = benchmark.cache(
    _prepare_dataset,
    force=force,
    ignore=["ignored_params"],
)
```

Call shape (deduplication by effective params):
```python
cache_ignore = getattr(dataset_cls, "prepare_cache_ignore", ())
for params in product_param(dataset_cls.parameters):
    if cache_ignore == "all":
        ignored, effective = params, {}
    else:
        ignored = {k: v for k, v in params.items() if k in cache_ignore}
        effective = {k: v for k, v in params.items() if k not in cache_ignore}
    # skip duplicate effective-param combinations
    cached_prepare(
        dataset_cls=dataset_cls,
        dataset_params=effective,
        ignored_params=ignored,
    )
```

This ensures `ignored_params` do not affect cache reuse while the dataset is still instantiated with the full parameter set.

Notes:
- This keeps one centralized cache namespace per benchmark.
- Parallel workers share the same cache root, avoiding duplicated work.
- Cache inspection/cleanup follows existing BenchOpt cache behavior.

---

### 6. Error Handling & Logging

#### Logging Strategy
- Use Python's `logging` module with `benchopt.datasets` logger
- Log levels:
  - DEBUG: Cache hits, detailed preparation steps
  - INFO: Preparation started/completed, timing
    - WARNING: Recoverable backend/caching warnings
    - ERROR: Dataset preparation failure

#### Exception Handling
1. Preparation failures are caught and reported
2. Failures are reported with dataset name + params + backend context
3. Command exits non-zero if any dataset preparation failed
4. Always provide actionable error messages (e.g., "Check internet connection for URL X")

---

### 7. SLURM and Backend Examples

Use the same backend mechanism as `benchopt run`.

Local parallelism:
```bash
benchopt prepare . -j 8
```

Distributed SLURM via submitit backend (`--parallel-config`):

```yaml
# slurm_config.yml
backend: submitit
slurm_cpus_per_task: 2
slurm_time: "01:00:00"
slurm_mem_per_cpu: "2GB"
slurm_partition: "cpu"
```

```bash
benchopt prepare . --parallel-config slurm_config.yml
```

---

## Implementation Roadmap

### Phase 1: Core Infrastructure
1. Add `prepare()` method to `BaseDataset`
2. Add preparation caching through benchmark cache API (`Benchmark.cache(...)`)
3. Update `_get_data()` to call `prepare()` on first use (with option to skip via flag)
4. Add unit tests for caching logic

### Phase 2: Benchmark Integration
1. Implement `prepare_all_data()` in `Benchmark` class
2. Integrate with `benchopt.parallel_backends.check_parallel_config` and `parallel_run`
3. Add progress tracking and error reporting
4. Keep `install_all_requirements()` focused on package installation only

### Phase 3: CLI Command
1. Create `benchopt prepare` command in `cli/main.py`
2. Add `--prepare` flag to `benchopt install`
3. Keep `--download` as deprecated alias for `--prepare`
4. Trigger `benchmark.prepare_all_data(...)` from CLI install flow
5. Add fallback to `get_data()` when no `prepare` method is implemented
6. Add comprehensive help and examples

### Phase 4: Testing & Documentation
1. Write unit tests for `prepare()` method
2. Write integration tests for parallel execution
3. Create user guide documenting the feature
4. Add CLI reference documentation
5. Provide example benchmarks using `prepare()`

### Phase 5: Migration & Deprecation
1. Mark `--download` in `benchopt install` as deprecated alias of `--prepare`
2. Update existing benchmarks to use `prepare()` where beneficial
3. Release notes documenting the new feature

---

## Backward Compatibility

- `prepare()` method is optional; existing datasets work without changes
- If `prepare()` is not implemented, dataset preparation falls back to `get_data()`
- `get_data()` behavior for run remains unchanged
- `--download` remains functional as deprecated alias of `--prepare`
- No breaking changes to public API

---

## Alternative Approaches Considered

### Alternative 1: Extend `get_data()`
- **Rejected**: Would couple preparation with data loading, reducing flexibility
- `prepare()` makes it clear that preparation is separate from loading

### Alternative 2: Use `pytest-xdist` style plugin
- **Rejected**: Too heavyweight; `concurrent.futures` is sufficient
- Adds unnecessary complexity for typical use cases

### Alternative 3: No caching, always re-prepare
- **Rejected**: Defeats the purpose of separating `prepare()` from `get_data()`
- Users need efficient re-runs of benchmarks

---

## Future Enhancements

1. **Distributed Preparation UX**: Provide ready-to-use templates and docs for
    existing distributed backends (Dask via BenchOpt parallel backends, and Ray
    via joblib backend integration)
2. **Incremental Preparation**: Track which parts are prepared, allow incremental updates
3. **Dataset Repository**: Central registry of prepared datasets for sharing
4. **Provenance Tracking**: Record which versions/commit hashes were used for preparation
5. **Integration with `snakemake` or `dvc`**: Workflow automation for data pipeline

---

## Configuration Example

Example benchmark selection in `config.yml`:

```yaml
# config.yml
dataset:
  - dataset1
  - dataset2[param=value]

solver:
  - solver1
  - solver2
```

Then:
```bash
benchopt prepare benchmark/ --config config.yml -j 8
# or
benchopt prepare benchmark/ --config config.yml --parallel-config slurm_config.yml
```

---

## Questions for Review

1. Should we keep all parallel-control options CLI-only (`-j`, `--parallel-config`) to stay fully coherent with `benchopt run`?
2. Should we expose an explicit cache namespace for prepare calls, or rely fully on `Benchmark.cache(...)` defaults?
3. Should we track prepare dependencies/versions for automatic cache invalidation?
4. Should `prepare()` be called automatically on first `get_data()` or only via explicit CLI?
   - Proposal: Explicit CLI call only, with option `auto_prepare` to change behavior
5. Should we support SLURM job arrays directly in benchopt, or keep it to user responsibility?
