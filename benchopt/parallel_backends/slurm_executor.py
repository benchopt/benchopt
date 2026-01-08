from contextlib import ExitStack

try:
    import submitit
    from submitit.helpers import as_completed
    from rich import progress
except ImportError:
    raise ImportError(
        "To run benchopt with the submitit backend, please install "
        "the `submitit` package: `pip install benchopt[submitit]` or "
        "`pip install submitit rich`."
    )


def get_slurm_executor(benchmark, config, timeout=100):
    # If the job timeout is not specified in the config dict, use 1.5x the
    # benchopt timeout. This value is a trade-off between helping the
    # scheduler (low slurm_time allow for faster accept) and avoiding
    # killing the job too early.
    if "slurm_time" not in config and timeout is not None:
        # Timeout is in second in benchopt
        config["slurm_time"] = f"00:{int(1.5 * timeout)}"

    slurm_folder = benchmark.get_slurm_folder()
    executor = submitit.AutoExecutor(slurm_folder)
    executor.update_parameters(**config)
    return executor


def harmonize_slurm_config(slurm_cfg):
    """Harmonize SLURM config for handling equivalent key names problem"""
    slurm_cfg = {k.removeprefix("slurm_"): v for k, v in slurm_cfg.items()}
    eq_dict = submitit.SlurmExecutor._equivalence_dict()
    new_slurm_cfg = {}
    for k, v in slurm_cfg.items():
        if k in eq_dict:
            new_slurm_cfg["slurm_" + eq_dict[k]] = v
        else:
            new_slurm_cfg["slurm_" + k] = v
    return new_slurm_cfg


def merge_slurm_configs(*slurm_cfgs):
    """Merge multiple SLURM config dicts in order, with later dicts overriding
    earlier ones.

    The keys are harmonized before merging.
    """
    slurm_cfg = {}
    for cfg in slurm_cfgs:
        cfg = harmonize_slurm_config(cfg)
        slurm_cfg.update(cfg)
    return slurm_cfg


def get_solver_slurm_config(solver, slurm_bench_cfg):
    """Generate and merge SLURM configuration for a solver from static,
    dynamic, and benchmark configs.
    """
    static_solver_cfg = getattr(solver, "slurm_params", {})
    dyn_solver_cfg = {
        k: v for k, v in solver._parameters.items() if k.startswith("slurm_")
    }
    solver_cfg = merge_slurm_configs(
        slurm_bench_cfg,
        static_solver_cfg,
        dyn_solver_cfg,
    )

    return solver_cfg


def hashable_pytree(pytree):
    """Flatten a pytree into a list."""
    if isinstance(pytree, (list, tuple)):
        return tuple(hashable_pytree(item) for item in sorted(pytree))
    elif isinstance(pytree, dict):
        return tuple(
            (k, hashable_pytree(v)) for k, v in sorted(pytree.items())
        )
    else:
        return pytree


def run_on_slurm(
    benchmark, slurm_config, run_one_solver, common_kwargs, all_runs
):

    executors = {}
    tasks = []

    with ExitStack() as stack:
        for kwargs in all_runs:
            solver = kwargs.get("solver")
            solver_slurm_config = get_solver_slurm_config(solver, slurm_config)
            executor_config = hashable_pytree(solver_slurm_config)

            if executor_config not in executors:
                executor = get_slurm_executor(
                    benchmark,
                    solver_slurm_config,
                    timeout=common_kwargs["timeout"],
                )
                stack.enter_context(executor.batch())
                executors[executor_config] = executor

            future = executors[executor_config].submit(
                run_one_solver,
                **common_kwargs,
                **kwargs,
            )
            tasks.append(future)

    print(f"First job id: {tasks[0].job_id}")

    for t in progress.track(as_completed(tasks), total=len(tasks)):
        exc = t.exception()
        if exc is not None:
            for tt in tasks:
                tt.cancel()
            raise exc

    return [t.results()[0] for t in tasks]
