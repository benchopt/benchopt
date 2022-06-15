import io
import os
import re
import warnings
import platform
import contextlib
import subprocess
from shutil import which
from pathlib import Path

from ..config import DEBUG
from .shell_cmd import _run_shell


def _get_processor_name():
    "Return processor name in a cross-platform way."
    out = ""
    if platform.system() == "Windows":
        out = platform.processor()
    elif platform.system() == "Darwin":
        os.environ["PATH"] = os.environ["PATH"] + os.pathsep + "/usr/sbin"
        command = ["sysctl", "-n", "machdep.cpu.brand_string"]
        out = subprocess.check_output(command).strip().decode("utf-8")
    elif platform.system() == "Linux":
        all_info = Path('/proc/cpuinfo').read_text()
        for line in all_info.splitlines():
            if "model name" in line:
                out = re.sub(r".*model name.*:\s*", "", line, 1)
    return out


def get_cuda_version():
    "Return GPU name and CUDA version."
    if which("nvidia-smi") is None:
        return None
    command = ["nvidia-smi", "-q", "-x"]
    try:
        out = subprocess.check_output(command).strip().decode("utf-8")
    except subprocess.CalledProcessError:
        warnings.warn(
            "`nvidia-smi` has failed. Please check NVIDIA driver install."
        )
        return None
    try:
        version = re.search('<cuda_version>(.*)</cuda_version>', out).group(1)
        name = re.search('<product_name>(.*)</product_name>', out).group(1)
        return f"{name}: cuda_{version}"
    except AttributeError:
        warnings.warn(
            "Could not parse cuda version or device name from `nvidia-smi`."
        )
        return None


def _get_numpy_libs():
    "Return info on 'Blas/Lapack' lib linked to numpy."

    # Import is nested to avoid long import time.
    import numpy as np

    with contextlib.redirect_stdout(io.StringIO()) as capture:
        np.show_config()
    lines = capture.getvalue().splitlines()
    libs = []
    for li, line in enumerate(lines):
        for key in ("lapack", "blas"):
            if line.startswith(f"{key}_opt_info"):
                lib = lines[li + 1]
                if "NOT AVAILABLE" in lib:
                    lib = "unknown"
                else:
                    try:
                        lib = lib.split("[")[1].split("'")[1]
                    except IndexError:
                        pass  # keep whatever it was
                libs += [f"{key}={lib}"]
    libs = ", ".join(libs)
    return libs


def _get_git_tag():
    err, tag = _run_shell("git describe --tags --abbrev=0", return_output=True)
    if err != 0:
        if DEBUG:
            print(err, tag)
        tag = None
    return tag


def get_sys_info():
    "Return a dictionary with info from the current system."

    # Import are nested to avoid long import time when func is not called
    import scipy
    import psutil
    import numpy as np
    from joblib import cpu_count

    info = {}

    # Info on the env
    info["env-OMP_NUM_THREADS"] = os.environ.get('OMP_NUM_THREADS')

    # Info on the OS
    info["platform"] = platform.system()
    info["platform-architecture"] = platform.machine()
    info["platform-release"] = platform.release()
    info["platform-version"] = platform.version()

    # Info on the hardware
    info["system-cpus"] = cpu_count()
    info["system-processor"] = _get_processor_name()
    info["system-ram (GB)"] = round(
        psutil.virtual_memory().total / (1024.0 ** 3)
    )

    # Info on dependency libs
    info["version-cuda"] = get_cuda_version()
    info["version-numpy"] = (np.__version__, _get_numpy_libs())
    info["version-scipy"] = scipy.__version__

    # Info on benchmark version
    info["benchmark-git-tag"] = _get_git_tag()

    return info
