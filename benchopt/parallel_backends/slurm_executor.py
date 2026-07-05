from collections import defaultdict
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


def _job_slurm_config(kwargs, slurm_config):
    """Resolve the SLURM config for a single run kwargs entry."""
    solver = kwargs.get("solver")
    if solver is None:
        return slurm_config
    return get_solver_slurm_config(solver, slurm_config)


def _run_batch(run_one_solver, batch_kwargs, n_jobs=1):
    """Run multiple solver configurations in a single SLURM job."""
    if n_jobs == 1:
        return [run_one_solver(**kw) for kw in batch_kwargs]
    return Parallel(n_jobs=n_jobs)(
        delayed(run_one_solver)(**kw)
        for kw in batch_kwargs
    )


def _group_runs(all_runs, slurm_config, group_by):
    """Group runs sharing the same `group_by` key and slurm config."""
    if group_by is None:
        return [[kw] for kw in all_runs]
    groups = defaultdict(list)
    for kwargs in all_runs:
        cfg = hashable_pytree(_job_slurm_config(kwargs, slurm_config))
        # `group_by` is one of 'dataset', 'solver' or 'objective'; the
        # corresponding name lives in the run metadata.
        group_key = str(kwargs["meta"][f"{group_by}_name"])
        groups[(group_key, cfg)].append(kwargs)
    return list(groups.values())


def run_on_slurm(
    benchmark, slurm_config, run_one_solver, run_kwargs_generator,
    group_by=None, batch_n_jobs=1
):

    all_runs = list(run_kwargs_generator)
    run_groups = _group_runs(all_runs, slurm_config, group_by)

    executors = {}
    tasks = []
    with ExitStack() as stack:
        for run_group in run_groups:
            job_slurm_config = _job_slurm_config(run_group[0], slurm_config)
            executor_config = hashable_pytree(job_slurm_config)

            if executor_config not in executors:
                executor = get_slurm_executor(
                    benchmark,
                    job_slurm_config,
                    timeout=run_group[0].get("timeout"),
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

        # Each grouped job runs a batch of solvers and returns the list of
        # their results; yield them individually to preserve the streaming
        # contract expected by the runner.
        for res in t.results()[0]:
            yield res
