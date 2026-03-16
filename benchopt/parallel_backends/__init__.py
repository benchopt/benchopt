import yaml
from joblib import parallel_config
from joblib import Parallel, delayed

_DISTRIBUTED_FRONTAL = False

DISTRIBUTED_BACKENDS = ('loky', 'dask', 'submitit')


def set_distributed_frontal():
    global _DISTRIBUTED_FRONTAL
    _DISTRIBUTED_FRONTAL = True


def is_distributed_frontal():
    return _DISTRIBUTED_FRONTAL


def parallel_run(benchmark, run, kwargs, all_runs, config, collect=False):
    config = config or {}
    backend = config.pop('backend', 'loky')
    group_by = config.pop('group_by', None)
    batch_n_jobs = config.pop('batch_n_jobs', 1)
    if collect:  # Collect should not run complicated parallelism
        backend = 'loky'
    assert backend in DISTRIBUTED_BACKENDS, (
        f"Unknown backend {backend}. Valid backends: {DISTRIBUTED_BACKENDS}."
    )
    if backend == 'submitit':
        from .slurm_executor import run_on_slurm
        results = run_on_slurm(
            benchmark, config, run, kwargs, all_runs,
            group_by=group_by, batch_n_jobs=batch_n_jobs,
        )
    else:
        if backend == 'dask':
            from .dask_backend import check_dask_config
            config = check_dask_config(config)
        with parallel_config(backend, **config):
            results = Parallel()(
                delayed(run)(**kwargs, **run_kwargs)
                for run_kwargs in all_runs
            )

    return results


def check_parallel_config(parallel_config_file, n_jobs):
    """Returns the parallelism config information for the run.

    If nothing is provided, default to `loky` backend with n_jobs=1.

    Parameters
    ----------
    parallel_config_file: str or dict or None
        Path to the parallel config YAML file, or a dict containing the config
        information. If None, defaults to None.
    n_jobs: int or None
        Number of parallel jobs to run. If None, defaults to None.

    Returns
    -------
    parallel_config: dict
        The parallel config information for the run.
    """

    # Load parallel config from config file. If None is provided,
    # default to joblib backend ('loky').
    if parallel_config_file is not None:
        if not isinstance(parallel_config_file, dict):
            with open(parallel_config_file, "r") as f:
                parallel_config = yaml.safe_load(f)
        else:
            parallel_config = parallel_config_file
        if n_jobs is not None:
            parallel_config['n_jobs'] = n_jobs
    else:
        parallel_config = {'backend': 'loky', 'n_jobs': n_jobs}

    assert 'backend' in parallel_config, (
        "Could not find `backend` specification in parallel_config file. "
        "Please specify it. See :ref:`parallel_run` for detailed description."
    )

    group_by = parallel_config.get('group_by')
    if group_by is not None:
        assert group_by in ('dataset', 'solver', 'objective'), (
            f"`group_by` must be 'dataset', 'solver', or 'objective'. "
            f"Got '{group_by}'."
        )
    batch_n_jobs = parallel_config.get('batch_n_jobs', 1)
    assert isinstance(batch_n_jobs, int) and batch_n_jobs >= 1, (
        f"`batch_n_jobs` must be a positive integer. Got {batch_n_jobs}."
    )

    backend = parallel_config['backend']
    if backend in ('dask', 'submitit'):
        print(f"Distributed run with backend: {backend}")
        set_distributed_frontal()

    return parallel_config
