import yaml
from collections import deque
from joblib import parallel_config
from joblib import Parallel, delayed

_DISTRIBUTED_FRONTAL = False

DISTRIBUTED_BACKENDS = ('loky', 'dask', 'submitit')


def set_distributed_frontal():
    global _DISTRIBUTED_FRONTAL
    _DISTRIBUTED_FRONTAL = True


def is_distributed_frontal():
    return _DISTRIBUTED_FRONTAL


def _tag_cached_runs(run, run_kwargs_generator, collect):
    """Tag each run, in generation order, as one of:

    - ``'cached'``: already computed, loaded here on the frontal node (cheap,
      it does not load the data) instead of being dispatched as a job (e.g. a
      SLURM job just to hit the cache).
    - ``'result'``: a ready result that is not a cache hit. In ``collect``
      mode, runs missing from the cache are reported as ``'not run yet'``
      rather than being computed.
    - ``'dispatch'``: a cache miss that must be run on the parallel backend.
    """
    check_in_cache = getattr(run, "check_call_in_cache", None)
    for run_kwargs in run_kwargs_generator:
        if (check_in_cache is not None
                and not run_kwargs.get('force', False)
                and check_in_cache(**run_kwargs)):
            yield 'cached', run(**run_kwargs)
        elif collect:
            # Collect mode only gathers cached runs; flag the rest as missing.
            meta = run_kwargs['meta']
            key = (
                meta['dataset_name'],
                meta['objective_name'],
                meta['solver_name'],
            )
            yield 'result', ([], key, 'not run yet', "")
        else:
            yield 'dispatch', run_kwargs


def _dispatch(backend, benchmark, run, run_kwargs_iter, config):
    """Run ``run(**kwargs)`` for each kwargs on the chosen backend, yielding
    results as they complete.

    This is the only backend-specific piece: a thin adapter turning an iterator
    of run kwargs into an iterator of results. Backends consume the kwargs
    lazily (loky/dask, bounded by ``pre_dispatch``) or in one batch (submitit).
    """
    if backend == 'submitit':
        from .slurm_executor import run_on_slurm
        yield from run_on_slurm(benchmark, config, run, run_kwargs_iter)
    else:
        if backend == 'dask':
            from .dask_backend import check_dask_config
            config = check_dask_config(config)
        # `batch_size` is a `Parallel` argument, not a `parallel_config` one.
        batch_size = config.pop('batch_size', 'auto')
        with parallel_config(backend, **config):
            yield from Parallel(
                return_as="generator_unordered", batch_size=batch_size
            )(
                delayed(run)(**run_kwargs) for run_kwargs in run_kwargs_iter
            )


def parallel_run(benchmark, run, run_kwargs_generator, config, collect=False):
    config = config or {}
    backend = config.pop('backend', 'loky')
    if collect:  # Collect should not run complicated parallelism
        backend = 'loky'
    assert backend in DISTRIBUTED_BACKENDS, (
        f"Unknown backend {backend}. Valid backends: {DISTRIBUTED_BACKENDS}."
    )

    # Cache hits are loaded on the frontal node and parked in `ready`; only the
    # misses are dispatched. The dispatch stays backend-agnostic and lazy (we
    # never hold all the runs, each carrying its loaded data, in memory): the
    # backend pulls `_to_dispatch` on demand, and cache hits seen meanwhile are
    # merged back into the result stream.
    ready = deque()

    def _to_dispatch():
        for tag, item in _tag_cached_runs(run, run_kwargs_generator, collect):
            if tag == 'dispatch':
                yield item
            else:
                ready.append(((tag == 'cached'), item))

    def _results():
        for item in _dispatch(backend, benchmark, run, _to_dispatch(), config):
            while ready:
                yield ready.popleft()
            yield False, item
        while ready:
            yield ready.popleft()

    return _results()


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
            if ("slurm_time" in parallel_config
                    and isinstance(parallel_config["slurm_time"], int)):
                # YAML may parse unquoted sexagesimal times (e.g. 10:30) as
                # integer seconds. Convert back to HH:MM:SS, because submitit
                # interprets raw int values as minutes.
                total_seconds = parallel_config["slurm_time"]
                hours, rem_seconds = divmod(total_seconds, 3600)
                minutes, seconds = divmod(rem_seconds, 60)
                parallel_config['slurm_time'] = (
                    f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                )
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

    backend = parallel_config['backend']
    if backend in ('dask', 'submitit'):
        print(f"Distributed run with backend: {backend}")
        set_distributed_frontal()

    return parallel_config
