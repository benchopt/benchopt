import os
import re
import platform
import subprocess
from shutil import which
from pathlib import Path

from .stream_redirection import SuppressStd


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


def _get_cuda_version():
    "Return CUDA version."
    if which("nvcc") is None:
        return None
    command = ["nvcc", "--version"]
    out = subprocess.check_output(command).strip().decode("utf-8")
    out = out.splitlines()[-1]  # take only last line
    return out


def _get_numpy_libs():
    "Return info on 'Blas/Lapack' lib linked to numpy."

    # Import is nested to avoid long import time.
    import numpy as np

    with SuppressStd() as capture:
        np.show_config()
    lines = capture.output.splitlines()
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
    info["version-cuda"] = _get_cuda_version()
    info["version-numpy"] = (np.__version__, _get_numpy_libs())
    info["version-scipy"] = scipy.__version__

    return info
