from joblib import parallel_config
from joblib import Parallel, delayed


def parallel_run(benchmark, run, kwargs, all_runs, config=None, n_jobs=None):

    # Load parallel config from config file. If None is provided, default to
    # default joblib backend ('loky').
    if config is None:
        config = {'backend': 'loky', 'n_jobs': n_jobs if n_jobs else 1}
    else:
        assert n_jobs is None, "Setting both `n_jobs` and config_file"

    assert 'backend' in config, (
        "Could not find `backend` specification in parallel_config file. "
        "Please specify it. See :ref:`parallel_run` for detailed description."
    )

    backend = config.pop('backend')

    if backend == 'submitit':
        from .utils.parallel_backends.slurm_executor import run_on_slurm
        results = run_on_slurm(benchmark, config, run, kwargs, all_runs)
    else:
        with parallel_config(backend, **config):
            results = Parallel()(
                delayed(run)(**kwargs, **run_kwargs)
                for run_kwargs in all_runs
            )

    return results
