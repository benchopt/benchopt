import os
import re
import venv
import shutil
import pkgutil
import warnings
import tempfile
import itertools
import subprocess
from importlib import import_module

from .config import get_global_setting
from .config import DEBUG, ALLOW_INSTALL, PRINT_INSTALL_ERROR


# Load global setting
VENV_DIR = get_global_setting('venv_dir')


if not os.path.exists(VENV_DIR):
    os.mkdir(VENV_DIR)


# Bash commands for installing and checking the solvers
PIP_INSTALL_CMD = "pip install -qq {packages}"
PIP_UNINSTALL_CMD = "pip uninstall -qq -y {packages}"
BASH_INSTALL_CMD = "bash install_scripts/{install_script} {env}"
CHECK_PACKAGE_INSTALLED_CMD = (
    "python -c 'import {package}'"
)
CHECK_CMD_INSTALLED_CMD = "type $'{cmd_name}'"


def _run_in_bash(script, raise_on_error=None, capture_stdout=True):
    """Run a bash script and return its exit code.

    Parameters
    ----------
    script: str
        Script to run
    raise_on_error: str or callable or None
        If raise_on_error is a string, raise a RuntimeError with the given
        message if the command's exit code is non-zero.
        If raise_on_error is a callable, when script output is non 0, call
        the callable with output as an argument `raise_on_error(output)`.
        Else, just return the exit code.
    capture_stdout: bool
        If set to True, capture the stdout of the subprocess. Else, it is
        printed in the main process stdout.

    Returns
    -------
    exit_code: int
        Exit code of the script
    """
    # Use a TemporaryFile to make sure this file is cleaned up at
    # the end of this function.
    tmp = tempfile.NamedTemporaryFile(mode="w+")
    fast_failure_script = f"set -e\n{script}"
    tmp.write(fast_failure_script)
    tmp.flush()

    if DEBUG:
        print(fast_failure_script)

    if capture_stdout:
        exit_code, output = subprocess.getstatusoutput([f"bash {tmp.name}"])
    else:
        exit_code = os.system(f"bash {tmp.name}")
        output = ""
    if raise_on_error is not None and exit_code != 0:
        if isinstance(raise_on_error, str):
            raise RuntimeError(raise_on_error.format(output=output))
        elif callable(raise_on_error):
            raise_on_error(output)
        else:
            raise ValueError("Bad value for `raise_on_error`. Should be a str"
                             f", a callable or None. Got {raise_on_error}.")
    return exit_code


def _run_bash_in_env(script, env_name=None, raise_on_error=None,
                     capture_stdout=True):
    """Run a script in a given virtual env

    Parameters
    ----------
    script: str
        Script to run
    env_name: str
        Name of the environment to run the script in.
    raise_on_error: str or None
        If raise_on_error is not None, raise a RuntimeError with the given
        message if the command's exit code is non-zero.
        Else, just return the exit code.
    capture_stdout: bool
        If set to True, capture the stdout of the subprocess. Else, it is
        printed in the main process stdout.

    Returns
    -------
    exit_code: int
        Exit code of the script
    """
    if env_name is not None:
        env_dir = f"{VENV_DIR}/{env_name}"

        script = f"source {env_dir}/bin/activate\n{script}"

    return _run_in_bash(script, raise_on_error=raise_on_error,
                        capture_stdout=capture_stdout)


def pip_install_in_env(*packages, env_name=None):
    """Install the packages with pip in the given environment"""
    if env_name is None and not ALLOW_INSTALL:
        raise ValueError("Trying to install solver not in a virtualenv. "
                         "To allow this, set BENCHO_ALLOW_INSTALL=True.")
    cmd = PIP_INSTALL_CMD.format(packages=' '.join(packages))
    error_msg = f"Failed to pip install packages {packages}\nError:{{output}}"
    if not PRINT_INSTALL_ERROR:
        error_msg = None
    _run_bash_in_env(cmd, env_name=env_name,
                     raise_on_error=error_msg)


def pip_uninstall_in_env(*packages, env_name=None):
    """Uninstall the packages with pip in the given environment"""
    if env_name is None and not ALLOW_INSTALL:
        raise ValueError("Trying to uninstall solver not in a virtualenv. "
                         "To allow this, set BENCHO_ALLOW_INSTALL=True.")
    cmd = PIP_UNINSTALL_CMD.format(packages=' '.join(packages))
    _run_bash_in_env(cmd, env_name=env_name,
                     raise_on_error=f"Failed to uninstall packages {packages}"
                     "\nError: {output}")


def bash_install_in_env(script, env_name=None):
    """Run a bash install script in the given environment"""
    if env_name is None and not ALLOW_INSTALL:
        raise ValueError("Trying to install solver not in a virtualenv. "
                         "To allow this, set BENCHO_ALLOW_INSTALL=True.")
    env = "$VIRTUAL_ENV" if env_name is not None else "$HOME/.local/"
    cmd = BASH_INSTALL_CMD.format(install_script=script, env=env)
    _run_bash_in_env(cmd, env_name=env_name,
                     raise_on_error=f"Failed to run script {script}\n"
                     "Error: {output}")


def check_import_solver(requirements_import, env_name=None):
    """Check that a python package is installed in an environment.

    Parameters
    ----------
    requirements_import : str
        Name of the packages that should be installed. This function checks
        that these packages can be imported in python.
    env_name : str or None
        Name of the virtual environment to check. If it is None, check in the
        current environment.
    """
    # TODO: if env is None, check directly in the current python interpreter
    for package in requirements_import:
        check_package_installed_cmd = CHECK_PACKAGE_INSTALLED_CMD.format(
            package=package)

        def raise_on_error(output):
            not_installed = f"ModuleNotFoundError: No module named '{package}'"
            if not_installed not in output:
                print(output)

        if _run_bash_in_env(check_package_installed_cmd,
                            env_name=env_name,
                            raise_on_error=raise_on_error) != 0:
            return False
    return True


def check_cmd_solver(cmd_name, env_name=None):
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
    return _run_bash_in_env(check_cmd_installed_cmd,
                            env_name=env_name) == 0


def get_all_benchmarks():
    """List all the available benchmarks."""
    submodules = pkgutil.iter_modules([f'benchmarks'])
    return [m.name for m in submodules]


def check_benchmarks(benchmarks, all_benchmarks):
    unknown_benchmarks = set(benchmarks) - set(all_benchmarks)
    assert len(unknown_benchmarks) == 0, (
        "{} is not a valid benchmark. Should be one of: {}"
        .format(unknown_benchmarks, all_benchmarks)
    )


def get_benchmark_module_name(benchmark):
    return f"benchmarks.{benchmark}"


def get_benchmark_objective(benchmark):
    """Load the objective function defined in the given benchmark."""
    benchmark_module_name = get_benchmark_module_name(benchmark)
    objective_module_name = f"{benchmark_module_name}.objective"
    module = import_module(objective_module_name)
    return module.Objective


def list_benchmark_submodule_names(benchmark, submodule='solvers'):
    submodules = pkgutil.iter_modules([f'benchmarks/{benchmark}/{submodule}'])
    return [m.name for m in submodules]


def _list_benchmark_submodule_classes(benchmark, package_name, class_name):

    classes = []
    # List all available module in benchmark.package_name
    submodule_names = list_benchmark_submodule_names(benchmark, package_name)
    module_name = get_benchmark_module_name(benchmark)
    for submodule_name in submodule_names:
        class_module_name = f"{module_name}.{package_name}.{submodule_name}"
        module = import_module(class_module_name)

        # Get the class
        classes.append(getattr(module, class_name))

    return classes


def list_benchmark_solvers(benchmark):
    """List all available solver classes for a given benchmark"""
    return _list_benchmark_submodule_classes(benchmark, 'solvers', 'Solver')


def list_benchmark_datasets(benchmark):
    """List all available dataset classes for a given benchmark"""
    return _list_benchmark_submodule_classes(benchmark, 'datasets', 'Dataset')


def check_solver_name_list(name_list):
    if name_list is None:
        return []
    return [name.lower() for name in name_list]


def filter_solvers(solvers, solver_names=None, forced_solvers=None,
                   exclude=None):

    # Currate the list of names
    exclude = check_solver_name_list(exclude)
    solver_names = check_solver_name_list(solver_names)
    forced_solvers = check_solver_name_list(forced_solvers)

    if len(exclude) > 0:
        # If a solver is explicitly included in solver_names, this takes
        # precedence over the exclusion parameter in the config file.
        exclude = set(exclude) - set(solver_names + forced_solvers)
        solvers = [s for s in solvers if s.name.lower() not in exclude]

    if len(solver_names) > 0:
        solvers = [s for s in solvers
                   if s.name.lower() in solver_names + forced_solvers]
        not_found = list(set(solver_names + forced_solvers) -
                         set([s.name.lower() for s in solvers]))
        if not_found:
            raise ValueError('Solver(s) not found: %s' % ', '.join(not_found))
    return solvers


def is_included(name, include_patterns=None):
    """Check if a certain name is match by any pattern in include_patterns.

    When include_patterns is None, all names are included.
    """
    if include_patterns is None or len(include_patterns) == 0:
        return True
    for p in include_patterns:
        if re.match(f".*{p}.*", name, flags=re.IGNORECASE) is not None:
            return True
    return False


def create_venv(env_name, recreate=False):
    """Create a virtual env with name env_name and install basic utilities"""

    env_dir = f"{VENV_DIR}/{env_name}"

    if not os.path.exists(env_dir) or recreate:
        print(f"Creating venv {env_name}:...", end='', flush=True)
        venv.create(env_dir, with_pip=True)
        # Install benchopt as well as packages used as utilities to install
        # other packages. The install of benchopt is done with the -e flag
        # to ease development process
        # XXX: add a flag to enable/disable develop install?
        pip_install_in_env("numpy", "cython", "-e .", env_name=env_name)
        print(" done")


def delete_venv(env_name):
    """Delete a virtual env with name env_name."""

    env_dir = f"{VENV_DIR}/{env_name}"
    if os.path.exists(env_dir):
        shutil.rmtree(env_dir)


def install_solvers(solvers, forced_solvers=None, env_name=None):
    """Install the listed solvers if needed."""

    for solver in solvers:
        force_install = solver.name.lower() in forced_solvers
        solver.install(env_name=env_name, force=force_install)


def install_required_datasets(benchmark, dataset_names, env_name=None):
    """List all datasets and install the required ones"""
    datasets = list_benchmark_datasets(benchmark)
    for dataset_class in datasets:
        for dataset_parameters in product_param(dataset_class.parameters):
            dataset = dataset_class(**dataset_parameters)
            if is_included(str(dataset), dataset_names):
                dataset_class.install(env_name=env_name, force=False)


class safe_import:
    """Do not fail on ImportError and Catch the warnings"""

    def __init__(self):
        self.failed_import = False
        self.record = warnings.catch_warnings(record=True)

    def __enter__(self):
        # Catch the import warning except if install error are printed.
        if not PRINT_INSTALL_ERROR:
            self.record.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):

        silence_error = False

        # prevent import error from propagating and tag
        if exc_type is not None and issubclass(exc_type, ImportError):
            self.failed_import = True

            # Prevent the error propagation
            silence_error = True

        if not PRINT_INSTALL_ERROR:
            self.record.__exit__(exc_type, exc_value, traceback)

        # Returning True in __exit__ prevent error propagation.
        return silence_error


def expand(keys, values):
    """Expand the multiple parameters for itertools product"""
    args = []
    for k, v in zip(keys, values):
        if ',' in k:
            params_name = [p.strip() for p in k.split(',')]
            assert len(params_name) == len(v)
            args.extend(list(zip(params_name, v)))
        else:
            args.append((k, v))
    return dict(args)


def product_param(parameters):
    """Get an iterator that is the product of parameters expanded as a dict.

    Parameters
    ----------
    parameters: dict of list
        A dictionary of type {parameter_names: parameters_value_list}. The
        parameter_names is either a single parameter name or a list of
        parameter names separated with ','. The parameters_value_list should
        be either a list of value if there is only one parameter or a list of
        tuple with the same cardinality as parameter_names.

    Returns
    -------
    parameter_iterator: iterator
        An iterator where each element is a dictionary of parameters expanded
        as the product of every items in parameters.
    """
    parameter_names = parameters.keys()
    return map(expand, itertools.repeat(parameter_names),
               itertools.product(*parameters.values()))
