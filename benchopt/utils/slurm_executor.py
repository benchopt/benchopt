import yaml
import sys

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


def get_slurm_executor(benchmark, slurm_config, timeout=100):

    with open(slurm_config, "r") as f:
        config = yaml.safe_load(f)

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


def run_on_slurm(
    benchmark,
    slurm_config,
    run_one_solver,
    common_kwargs,
    all_runs
):

    if not _SLURM_INSTALLED:
        raise ImportError(
            "Benchopt needs submitit and rich to launch computation on a "
            "SLURM cluster. Please use `pip install submitit rich` to use "
            "the --slurm option."
        )

    executor = get_slurm_executor(
        benchmark, slurm_config, common_kwargs["timeout"]
    )
    with executor.batch():
        tasks = [
            executor.submit(run_one_solver, **common_kwargs, **kwargs)
            for kwargs in all_runs
        ]

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
