import warnings

import yaml
from joblib import parallel_config
from joblib import Parallel, delayed


def parallel_run(benchmark, run, kwargs, all_runs, config_file=None, n_jobs=None):

    # Load parallel config from config file. If None is provided, default to
    # default joblib backend ('loky').
    if config_file is None:
        config = {'backend': 'loky', 'n_jobs': n_jobs}
    else:
        assert n_jobs is None, "Setting both `n_jobs` and config_file"
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

    if 'backend' not in config:
        warnings.warn(
            "No backend specified in the config file. This will cause an "
            "error starting benchopt 1.7. Default to 'submitit' backend.",
            DeprecationWarning
        )
        backend = "submitit"
    else:
        backend = config.pop('backend', 'loky')

    if backend == 'submitit':
        from .utils.parallel_backends.slurm_executor import run_on_slurm
        results = run_on_slurm(benchmark, config_file, run, kwargs, all_runs)
    else:
        with parallel_config(backend, **config):
            results = Parallel()(
                delayed(run)(**kwargs, **run_kwargs)
                for run_kwargs in all_runs
            )

    return results
