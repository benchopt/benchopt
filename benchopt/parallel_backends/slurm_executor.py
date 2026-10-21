from contextlib import ExitStack
from itertools import islice

try:
    import submitit
    from submitit.helpers import as_completed
except ImportError:
    raise ImportError(
        "To run benchopt with the submitit backend, please install "
        "the `submitit` package: `pip install benchopt[submitit]` or "
        "`pip install submitit`."
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
    benchmark, slurm_config, run_one_solver, run_kwargs_generator
):
    # Global cap on jobs in the SLURM queue (pending + running), across all
    # executors. New jobs are submitted as previous ones finish.
    max_jobs = slurm_config.pop("max_submitted_jobs", None)
    run_kwargs_generator = iter(run_kwargs_generator)

    executors = {}
    tasks = []

    while True:
        n_free = None if max_jobs is None else max_jobs - len(tasks)
        # Pack the jobs submitted in this round in one array per executor.
        with ExitStack() as stack:
            in_batch = set()
            for kwargs in islice(run_kwargs_generator, n_free):
                solver = kwargs.get("solver")
                if solver is not None:
                    job_slurm_config = get_solver_slurm_config(
                        solver, slurm_config
                    )
                else:
                    job_slurm_config = slurm_config
                executor_config = hashable_pytree(job_slurm_config)

                if executor_config not in executors:
                    executors[executor_config] = get_slurm_executor(
                        benchmark,
                        job_slurm_config,
                        timeout=kwargs.get("timeout"),
                    )
                executor = executors[executor_config]
                if executor_config not in in_batch:
                    stack.enter_context(executor.batch())
                    in_batch.add(executor_config)

                tasks.append(executor.submit(run_one_solver, **kwargs))
                # Jobs reload the data: don't keep it on the front node while
                # the batch holds the kwargs.
                if "dataset" in kwargs:
                    kwargs["dataset"]._data = None

        if not tasks:
            return

        # Yield results as jobs finish (unordered)
        t = next(as_completed(tasks))
        tasks.remove(t)
        exc = t.exception()
        if exc is not None:
            # Cancel remaining tasks and raise error
            for tt in tasks:
                tt.cancel()
            raise exc

        yield t.results()[0]
