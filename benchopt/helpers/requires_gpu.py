from ..utils.sys_info import get_cuda_version
from ..parallel_backends import is_distributed_frontal
from ..parallel_backends import get_worker_config

# SLURM options that request GPUs, with their `--gpus` short form.
_SLURM_GPU_KEYS = ('num_gpus', 'gpus', 'gpus_per_node', 'gpus_per_task')


def requires_gpu():
    """Helper for solvers that require a GPU to run.

    This helper allows to skip the GPU requirement check when launching
    the run from the frontal for a distributed run.
    """
    if is_distributed_frontal():
        return
    cuda_version = get_cuda_version()
    if cuda_version is not None:
        return cuda_version.split("cuda_", 1)[1][:4]
    else:
        raise ImportError("Solver needs a nvidia GPU.")


def gpu_available(solver):
    """Whether the runs of ``solver`` will have a GPU.

    Use it in ``Solver.skip`` to check this consistently from
    the machine running ``benchopt run``. With ``submitit``, a GPU is
    requested by ``gres`` or a ``gpus*`` option. With ``dask``, workers are
    assumed to have one.

    Parameters
    ----------
    solver : benchopt.BaseSolver
        The solver whose runs are checked.

    Returns
    -------
    available : bool
        True if the runs of ``solver`` will have a GPU.
    """
    config = get_worker_config(solver)
    if config is None:
        # run on the current node, use a direct check
        available = get_cuda_version() is not None
    elif config['backend'] == 'submitit':
        # scheduled jobs, check that their SLURM config requests a GPU
        options = {
            **config.get('slurm_additional_parameters', {}),
            **{k.removeprefix('slurm_'): v for k, v in config.items()},
        }
        options = {k.replace('-', '_'): v for k, v in options.items()}
        available = 'gpu' in str(options.get('gres', '')) or any(
            options.get(k) for k in _SLURM_GPU_KEYS
        )
    elif config['backend'] == 'dask':
        # workers unknown from the front node, assume they have a GPU
        available = True
    else:
        # no rule for this backend, fail instead of guessing
        raise ValueError(f"Unknown parallel backend {config['backend']!r}.")
    return available
