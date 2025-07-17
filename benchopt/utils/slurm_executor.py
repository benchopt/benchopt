import sys
import yaml
from contextlib import ExitStack

from benchopt.benchmark import get_setting
from benchopt.utils.terminal_output import print_normalize

try:
    import submitit
    from submitit.helpers import as_completed
    from submitit.core.utils import FailedJobError
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
            executor_config = tuple(sorted(solver_slurm_config.items()))

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

    main_job_ids = {str(t.job_id).split('_')[0] for t in tasks}
    print_normalize(f"Job array IDs: {main_job_ids}")

    try: 
        for t in progress.track(as_completed(tasks), total=len(tasks)):
            exc = t.exception()
            debug = get_setting("debug")
            if exc is not None and debug:
                raise exc

    except (KeyboardInterrupt, SystemExit) as e:
        print_normalize(f"{type(e).__name__}: Cancelling all tasks")
        for t in tasks:
            t.cancel()
        sys.exit(1)

    except FailedJobError:
        print_normalize("A job failed with debug mode activated. Cancelling all tasks.")
        for t in tasks:
            t.cancel()
        raise

    except Exception as e:
        print_normalize(f"{type(e).__name__}: Tasks will not be cancelled.")
        raise

    return [t.result() for t in tasks]
