import platform
import os
import re
import subprocess
import sys
from io import StringIO
import json
from shutil import which
import psutil

import numpy as np
import scipy


def is_tool(name):
    """Check whether `name` is on PATH and marked as executable."""
    return which(name) is not None


class SilenceStdout(object):
    """Silence stdout."""

    def __init__(self, close=True):
        self.close = close

    def __enter__(self):  # noqa: D105
        self.stdout = sys.stdout
        sys.stdout = StringIO()
        return sys.stdout

    def __exit__(self, *args):  # noqa: D105
        if self.close:
            sys.stdout.close()
        sys.stdout = self.stdout


def get_processor_name():
    out = ""
    if platform.system() == "Windows":
        out = platform.processor()
    elif platform.system() == "Darwin":
        os.environ["PATH"] = os.environ["PATH"] + os.pathsep + "/usr/sbin"
        command = ["sysctl", "-n", "machdep.cpu.brand_string"]
        out = subprocess.check_output(command).strip().decode("utf-8")
    elif platform.system() == "Linux":
        command = "cat /proc/cpuinfo"
        all_info = subprocess.check_output(command, shell=True).strip()
        all_info = all_info.decode("utf-8")
        for line in all_info.split("\n"):
            if "model name" in line:
                out = re.sub(".*model name.*:", "", line, 1)
    return out


def get_cuda_version():
    if which("nvcc") is None:
        return None
    command = ["nvcc", "--version"]
    out = subprocess.check_output(command).strip().decode("utf-8")
    out = out.split("\n")[-1]  # take only last line
    return out


def _get_numpy_libs():
    with SilenceStdout(close=False) as capture:
        np.show_config()
    lines = capture.getvalue().split("\n")
    capture.close()
    libs = []
    for li, line in enumerate(lines):
        for key in ("lapack", "blas"):
            if line.startswith("%s_opt_info" % key):
                lib = lines[li + 1]
                if "NOT AVAILABLE" in lib:
                    lib = "unknown"
                else:
                    try:
                        lib = lib.split("[")[1].split("'")[1]
                    except IndexError:
                        pass  # keep whatever it was
                libs += ["%s=%s" % (key, lib)]
    libs = ", ".join(libs)
    return libs


def get_sys_info():
    info = {}
    info["platform"] = platform.system()
    info["platform-release"] = platform.release()
    info["platform-version"] = platform.version()
    info["architecture"] = platform.machine()
    info["processor"] = get_processor_name()
    info["numpy"] = (np.__version__, _get_numpy_libs())
    info["OMP_NUM_THREADS"] = os.environ.get('OMP_NUM_THREADS')
    info["scipy"] = scipy.__version__
    info["cuda"] = get_cuda_version()
    info["RAM (GB)"] = round(psutil.virtual_memory().total / (1024.0 ** 3))
    return json.dumps(info)
