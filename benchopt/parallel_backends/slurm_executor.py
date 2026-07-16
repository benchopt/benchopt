import math
from contextlib import ExitStack

from joblib import Parallel, delayed

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


def _run_batch(run_one_solver, batch_kwargs, n_jobs=1):
    """Run multiple solver configurations in a single SLURM job."""
    return Parallel(n_jobs=n_jobs)(
        delayed(run_one_solver)(**kw)
        for kw in batch_kwargs
    )


def _group_runs(all_runs, slurm_config, group_by):
    """Split runs into batches as ``(job_slurm_config, runs)`` pairs.

    Runs sharing a `group_by` value and the same SLURM config go in one job.
    Runs without a `group_by` value each get their own job.
    """
    groups, singles = {}, []
    for kwargs in all_runs:
        solver = kwargs.get("solver")
        if solver is not None:
            job_slurm_config = get_solver_slurm_config(solver, slurm_config)
        else:
            job_slurm_config = slurm_config

        key = None
        if group_by is not None:
            # `benchopt run` names the entities in the run metadata, other
            # entry points (e.g. dataset preparation) pass them directly.
            meta = kwargs.get("meta", {})
            key = meta.get(f"{group_by}_name", kwargs.get(group_by))
        if key is None:
            singles.append((job_slurm_config, [kwargs]))
            continue
        cfg = hashable_pytree(job_slurm_config)
        groups.setdefault(
            (str(key), cfg), (job_slurm_config, [])
        )[1].append(kwargs)
    return singles + list(groups.values())


def run_on_slurm(
    benchmark, slurm_config, run_one_solver, run_kwargs_generator,
    group_by=None, batch_n_jobs=1
):

    run_groups = _group_runs(
        list(run_kwargs_generator), slurm_config, group_by
    )

    executors = {}
    tasks = []
    with ExitStack() as stack:
        for job_slurm_config, run_group in run_groups:
            # A job runs its group in `waves` rounds, so it needs `waves` times
            # the per-run timeout; different lengths get their own array.
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
                _run_batch,
                run_one_solver=run_one_solver,
                batch_kwargs=run_group,
                n_jobs=batch_n_jobs,
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
