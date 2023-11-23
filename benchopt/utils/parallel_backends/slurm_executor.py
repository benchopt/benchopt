try:
    import submitit
    from submitit.helpers import as_completed
    from rich import progress

    _submitit_INSTALLED = True
except ImportError:
    _submitit_INSTALLED = False


def get_slurm_executor(benchmark, config, timeout):

    # If the job timeout is not specified in the config file, use 1.5x the
    # benchopt timeout. This value is a trade-off between helping the
    # scheduler (low slurm_time allow for faster accept) and avoiding
    # killing the job too early.
    if 'slurm_time' not in config:
        # Timeout is in second in benchopt
        config['slurm_time'] = f"00:{int(1.5*timeout)}"

    slurm_folder = benchmark.get_slurm_folder()
    executor = submitit.AutoExecutor(slurm_folder)
    executor.update_parameters(**config)
    return executor


def run_on_slurm(benchmark, config, run_one_solver, common_kwargs, all_runs):

    if not _submitit_INSTALLED:
        raise ImportError(
            "Benchopt needs submitit and rich to launch computation on a "
            "SLURM cluster. Please use `pip install submitit rich` to use "
            "the `submitit` backend."
        )

    executor = get_slurm_executor(
        benchmark, config, timeout=common_kwargs["timeout"]
    )
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
