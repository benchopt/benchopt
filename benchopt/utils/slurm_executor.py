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


def harmonize_slurm_config(slurm_cfg):
    """Harmonize SLURM config for handling equivalent key names problem"""
    slurm_cfg = {k.removeprefix("slurm_"): v for k, v in slurm_cfg.items()}
    eq_dict = submitit.SlurmExecutor._equivalence_dict()
    new_slurm_cfg = {}
    for k, v in slurm_cfg.items():
        if k in eq_dict:
            new_slurm_cfg[eq_dict[k]] = v
        else:
            new_slurm_cfg[k] = v
    return new_slurm_cfg


def merge_slurm_configs(*slurm_cfgs):
    """Merge multiple SLURM config dicts in order, with later dicts overriding earlier ones."""
    slurm_cfg = {}
    for cfg in slurm_cfgs:
        cfg = harmonize_slurm_config(cfg)
        slurm_cfg.update(cfg)
    return slurm_cfg


def get_slurm_solver_config(solver, slurm_bench_cfg):
    """Generate and merge SLURM configuration for a solver from static, dynamic, and benchmark configs."""
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


def get_slurm_executor(benchmark, slurm_config, timeout=100):
    slurm_folder = benchmark.get_slurm_folder()
    executor = submitit.AutoExecutor(slurm_folder)

    executor.update_parameters(**slurm_config)

    # If the job timeout is not specified in the config file, use 1.5x the
    # benchopt timeout. This value is a trade-off between helping the
    # scheduler (low slurm_time allow for faster accept) and avoiding
    # killing the job too early.
    if "time" not in executor.parameters:
        # Timeout is in second in benchopt
        executor.update_parameters(timeout_min=int((timeout * 1.5) // 60) + 1)

    return executor


def run_on_slurm(benchmark, slurm_cfg_path, run_one_solver, common_kwargs, all_runs):
    if not _SLURM_INSTALLED:
        raise ImportError(
            "Benchopt needs submitit and rich to launch computation on a "
            "SLURM cluster. Please use `pip install submitit rich` to use "
            "the --slurm option."
        )

    executor_dict = {}
    tasks = []

    # Get benchmark slurm config
    with open(slurm_cfg_path, "r") as f:
        bench_slurm_cfg = yaml.safe_load(f)

    with ExitStack() as stack:
        for kwargs in all_runs:
            solver = kwargs.get("solver")
            slurm_cfg = get_slurm_solver_config(solver, bench_slurm_cfg)
            cfg_key = tuple(sorted(slurm_cfg.items()))
            if cfg_key not in executor_dict:
                executor = get_slurm_executor(
                    benchmark, slurm_cfg, common_kwargs["timeout"]
                )
                stack.enter_context(executor.batch())
                executor_dict[cfg_key] = executor

            future = executor_dict[cfg_key].submit(
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
