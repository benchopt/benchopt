import yaml

try:
    import submitit
    from submitit.helpers import as_completed
    from rich import progress

    _SLURM_INSTALLED = True
except ImportError:
    _SLURM_INSTALLED = False


_LAUNCHING_SLURM = False


def set_slurm_launch():
    global _LAUNCHING_SLURM
    _LAUNCHING_SLURM = True


def get_slurm_launch():
    return _LAUNCHING_SLURM


def get_slurm_executor(slurm_config, timeout=100, job_name="benchopt_run"):

    with open(slurm_config, "r") as f:
        config = yaml.safe_load(f)

    # If the job timeout is not specified in the config file, use 1.5x the
    # benchopt timeout. This value is a trade-off between helping the
    # scheduler (low slurm_time allow for faster accept) and avoiding
    # killing the job too early.
    if 'slurm_time' not in config:
        # Timeout is in second in benchopt
        config['slurm_time'] = f"00:{int(1.5*timeout)}"

    executor = submitit.AutoExecutor(job_name)
    executor.update_parameters(**config)
    return executor


def run_on_slurm(slurm_config, run_one_solver, common_kwargs, all_runs):

    if not _SLURM_INSTALLED:
        raise ImportError(
            "Benchopt needs submitit and rich to launch computation on a "
            "SLURM cluster. Please use `pip install submitit rich` to use "
            "the --slurm option."
        )

    executor = get_slurm_executor(slurm_config, common_kwargs["timeout"])
    with executor.batch():
        tasks = [
            executor.submit(run_one_solver, **common_kwargs, **kwargs)
            for kwargs in all_runs
        ]

    print(f"First job id: {tasks[0].job_id}")

    for t in progress.track(as_completed(tasks), total=len(tasks)):
        exc = t.exception()
        if exc is not None:
            for tt in tasks:
                tt.cancel()
            raise exc

    return [t.result() for t in tasks]
