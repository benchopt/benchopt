import yaml
from contextlib import ExitStack

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


def get_slurm_executor(benchmark, config, timeout=100):
    # If the job timeout is not specified in the config dict, use 1.5x the
    # benchopt timeout. This value is a trade-off between helping the
    # scheduler (low slurm_time allow for faster accept) and avoiding
    # killing the job too early.
    if "slurm_time" not in config:
        # Timeout is in second in benchopt
        config["slurm_time"] = f"00:{int(1.5 * timeout)}"

    slurm_folder = benchmark.get_slurm_folder()
    executor = submitit.AutoExecutor(slurm_folder)
    executor.update_parameters(**config)
    return executor


def merge_configs(slurm_config, solver):
    """Merge the slurm config with solver-specific slurm params."""
    solver_slurm_params = {
        **slurm_config,
        **getattr(solver, "slurm_params", {}),
    }
    return solver_slurm_params


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
    if not _SLURM_INSTALLED:
        raise ImportError(
            "Benchopt needs submitit and rich to launch computation on a "
            "SLURM cluster. Please use `pip install submitit rich` to use "
            "the --slurm option."
        )

    executors = {}
    tasks = []

    # Load the slurm config from a file if provided
    with open(slurm_config, "r") as f:
        slurm_config = yaml.safe_load(f)

    with ExitStack() as stack:
        for kwargs in all_runs:
            solver = kwargs.get("solver")
            solver_slurm_config = merge_configs(slurm_config, solver)
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

    return [t.result() for t in tasks]
