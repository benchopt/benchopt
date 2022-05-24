from ..utils.sys_info import get_cuda_version


_RUN_SLURM = False


def set_run_slurm():
    global _RUN_SLURM
    _RUN_SLURM = True


def requires_gpu():
    """Helper for solvers that require a GPU to run.

    This helper allows to skip the GPU requirement check
    when launching the computation on a SLURM cluster.
    """
    cuda_version = get_cuda_version()
    if cuda_version is not None:
        return cuda_version.split("cuda_", 1)[1][:4]
    else:
        if not _RUN_SLURM:
            raise ImportError("cuML solver needs a nvidia GPU.")
