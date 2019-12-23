import os
import venv
import pkgutil
import warnings
import tempfile
from glob import glob
from importlib import import_module

DEBUG = True
VENV_DIR = './.venv/'
PRINT_INSTALL_ERRORS = True


if not os.path.exists(VENV_DIR):
    os.mkdir(VENV_DIR)


PIP_INSTALL_CMD = "pip install -qq {packages}"
CHECK_PACKAGE_INSTALLED_CMD = (
    "python -c 'import {package_name}' 1>/dev/null 2>&1"
)
CHECK_CMD_INSTALLED_CMD = "type $'{solver_cmd}' 1>/dev/null 2>&1"


def _run_in_bash(script):
    """Run a bash script and return its exit code.

    Parameters
    ----------
    script: str
        Script to run

    Return
    ------
    exit_code: int
        Exit code of the script
    """
    # Use a TemporaryFile to make sure this file is cleaned up at
    # the end of this function.
    tmp = tempfile.NamedTemporaryFile(mode="w+")
    with open(tmp.name, 'w') as f:
        f.write(script)

    if DEBUG:
        print(script)

    return os.system(f"bash {tmp.name}")


def _run_bash_in_env(env_name, script):
    """Run a script in a given virtual env

    Parameters
    ----------
    env_name: str
        Name of the environment to run the script in
    script: str
        Script to run

    Return
    ------
    exit_code: int
        Exit code of the script
    """
    env_dir = f"{VENV_DIR}/{env_name}"

    env_script = f"""
        source {env_dir}/bin/activate
        {script}
    """

    return _run_in_bash(env_script)


def check_package_in_env(package_name, env_name=None):
    """Check that a python package is installed in an environment.

    Parameters
    ----------
    package_name : str
        Name of the package that should be installed. This function checks that
        this package can be imported in python.
    env_name : str or None
        Name of the virtual environment to check. If it is None, check in the
        current environment.
    """
    check_package_installed_cmd = CHECK_PACKAGE_INSTALLED_CMD.format(
        package_name=package_name)
    if env_name is None:
        return _run_in_bash(check_package_installed_cmd) == 0
    return _run_bash_in_env(env_name, check_package_installed_cmd) == 0


def check_cmd_in_env(cmd_name, env_name):
    """Check that a cmd is available in an environment.

    Parameters
    ----------
    cmd_name : str
        Name of the cmd that should be installed. This function checks that
        this cmd is available on the path of the environment.
    env_name : str or None
        Name of the virtual environment to check. If it is None, check in the
        current environment.
    """
    check_cmd_installed_cmd = CHECK_CMD_INSTALLED_CMD.format(
        cmd_name=cmd_name)
    if env_name is None:
        return _run_in_bash(check_cmd_installed_cmd) == 0

    return _run_bash_in_env(env_name, check_cmd_installed_cmd) == 0


def get_all_benchmarks():
    """List all the available benchmarks."""
    benchmark_files = glob("benchmarks/*/bench*.py")
    benchmarks = []
    for benchmark_file in benchmark_files:
        benchmark_name = benchmark_file.split(os.path.sep)[1]
        benchmarks.append(benchmark_name)
    return benchmarks


def check_benchmarks(benchmarks, all_benchmarks):
    unknown_benchmarks = set(benchmarks) - set(all_benchmarks)
    assert len(unknown_benchmarks) == 0, (
        "{} is not a valid benchmark. Should be one of: {}"
        .format(unknown_benchmarks, all_benchmarks)
    )


def get_benchmark_module_name(benchmark):
    return f"benchmarks.{benchmark}"


def load_benchmark_losses(benchmark):
    module_name = get_benchmark_module_name(benchmark)
    module = import_module(module_name)
    return module.loss_function, module.DATASETS


def list_solvers(benchmark):
    submodules = pkgutil.iter_modules([f'benchmarks/{benchmark}/solvers'])
    return [m.name for m in submodules]


def get_all_solvers(benchmark, solver_names=None):

    solver_classes = []
    solvers = list_solvers(benchmark)
    module_name = get_benchmark_module_name(benchmark)
    for s in solvers:
        solver_module_name = f"{module_name}.solvers.{s}"
        solver_module = import_module(solver_module_name)

        # Check if there where no import issues
        installed = getattr(solver_module, 'solver_import', None)
        installed = (installed is None or not installed.failed_import)

        # Get the Solver class
        solver_class = solver_module.Solver
        solver_name = solver_class.name.lower()
        solver_class.installed = installed
        if solver_names is None or solver_name in solver_names:
            solver_classes.append(solver_class)

    return solver_classes


def create_venv(env_name, recreate=False):
    """Create a virtual env with name env_name and install basic utilities"""

    env_dir = f"{VENV_DIR}/{env_name}"

    if not os.path.exists(env_dir) or recreate:
        print(f"Creating venv {env_name}:...", end='', flush=True)
        venv.create(env_dir, with_pip=True)
        # Install benchopt as well as packages used as utilities to install
        # other packages.
        cmd = PIP_INSTALL_CMD.format(packages="numpy cython .")
        assert _run_bash_in_env(env_name, cmd) == 0, (
            "Failed to install numpy, cython and benchopt"
        )
        print(" done")


def install_solvers(env_name, solvers):
    """Install the listed solvers if needed."""

    # Install the packages necessary for the benchmark's solvers with pip
    pip_install_solvers = [s for s in solvers if s.install_cmd == 'pip']
    print(f"Installing solvers {pip_install_solvers!r} with pip:...",
          end='', flush=True)
    pip_install = []
    for s in pip_install_solvers:
        if not s.is_installed(env_name):
            pip_install.append(s.install_package)
    if len(pip_install) > 0:
        script = PIP_INSTALL_CMD.format(packages=' '.join(pip_install))
        exit_code = _run_bash_in_env(env_name, script)
        if exit_code != 0:
            print(" errored")
            raise RuntimeError("The installation failed in the venv")
    print(" done")

    # Run install script for necessary for the benchmark's solvers that cannot
    # be installed via pip
    sh_install_solvers = [s for s in solvers if s.install_cmd == 'bash']
    print(f"Running bash install script for {sh_install_solvers}:...",
          end='', flush=True)
    for s in sh_install_solvers:
        if not s.is_installed(env_name):
            script = f"bash install_scripts/{s.install_script} $VIRTUAL_ENV"
        _run_bash_in_env(env_name, script)
    print(" done")


class safe_import():
    """Do not fail on ImportError and Catch the warnings"""
    def __init__(self):
        self.failed_import = False
        self.record = warnings.catch_warnings(record=True)

    def __enter__(self):
        self.record.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):

        silence_error = False

        # prevent import error from propagating and tag
        if exc_type is ImportError:
            self.failed_import = True

            if PRINT_INSTALL_ERRORS:
                import traceback
                traceback.print_exc()

            # Prevent the error propagation
            silence_error = True

        self.record.__exit__(exc_type, exc_value, traceback)
        return silence_error
