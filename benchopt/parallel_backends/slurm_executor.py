import math
from contextlib import ExitStack

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


def _split_by_slurm_config(batch, slurm_config):
    """Sub-partition a `group_runs` batch into ``(job_slurm_config, runs)``
    pairs, one per distinct SLURM config found in the batch.

    A batch shares its `group_by` key, but can still span several solvers
    with different `slurm_params` (e.g. ``group_by=['dataset']``), so it is
    never itself the SLURM job unit -- each same-config run of items is.
    """
    groups, order = {}, []
    for kwargs in batch:
        solver = kwargs.get("solver")
        if solver is not None:
            job_slurm_config = get_solver_slurm_config(solver, slurm_config)
        else:
            job_slurm_config = slurm_config

        cfg = hashable_pytree(job_slurm_config)
        if cfg not in groups:
            groups[cfg] = (job_slurm_config, [])
            order.append(cfg)
        groups[cfg][1].append(kwargs)
    return [groups[cfg] for cfg in order]


def run_on_slurm(
    benchmark, slurm_config, run_batch, batches, batch_n_jobs=1
):
    """Submit each pre-grouped batch (see `group_runs`) as SLURM job(s).

    ``run_batch`` is the batched run function (see the ``run_batch`` factory in
    this package), passed in rather than imported to keep the dependency
    one-directional. ``batch_n_jobs`` only sizes the job wall-time here (each
    job runs its group in ``ceil(len / batch_n_jobs)`` waves). A batch is
    further split by SLURM config (`_split_by_slurm_config`), since it can span
    several solvers with different `slurm_params`.
    """
    executors = {}
    tasks = []
    with ExitStack() as stack:
        for batch in batches:
            for job_slurm_config, run_group in _split_by_slurm_config(
                batch, slurm_config
            ):
                # A job runs its group in `waves` rounds, so it needs `waves`
                # times the per-run timeout; different lengths get their own
                # array.
                waves = math.ceil(len(run_group) / batch_n_jobs)
                executor_config = (hashable_pytree(job_slurm_config), waves)

                if executor_config not in executors:
                    timeout = run_group[0].get("timeout")
                    if timeout is not None:
                        timeout *= waves
                    executor = get_slurm_executor(
                        benchmark,
                        job_slurm_config,
                        timeout=timeout,
                    )
                    stack.enter_context(executor.batch())
                    executors[executor_config] = executor

                tasks.append(executors[executor_config].submit(
                    run_batch, run_group,
                ))

    # Yield results as jobs finish (unordered)
    for t in as_completed(tasks):
        exc = t.exception()
        if exc is not None:
            # Cancel remaining tasks and raise error
            for tt in tasks:
                tt.cancel()
            raise exc

        # A job returns the list of its batch's results; yield each in turn.
        for res in t.results()[0]:
            yield res
