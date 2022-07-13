from ..utils.sys_info import get_cuda_version
from ..utils.slurm_executor import get_slurm_launch


def requires_gpu():
    """Helper for solvers that require a GPU to run.

    This helper allows to skip the GPU requirement check
    when launching the computation on a SLURM cluster.
    """
    cuda_version = get_cuda_version()
    if cuda_version is not None:
        return cuda_version.split("cuda_", 1)[1][:4]
    else:
        if not get_slurm_launch():
            raise ImportError("cuML solver needs a nvidia GPU.")
