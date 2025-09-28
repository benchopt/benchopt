from ..utils.sys_info import get_cuda_version
from ..parallel_backends import is_distributed_frontal


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
