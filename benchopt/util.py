import re
import warnings
import itertools
from pathlib import Path

from .config import RAISE_INSTALL_ERROR
from .utils.shell_cmd import _run_shell_in_conda_env
from .utils.dynamic_modules import _load_class_from_module


# Shell cmd to test if a cmd exists
CHECK_SHELL_CMD_EXISTS = "type $'{cmd_name}'"


def import_shell_cmd(cmd_name, env_name=None):
    """Check that a cmd is available in an environment.

    Parameters
    ----------
    cmd_name : str
        Name of the cmd that should be installed. This function checks that
        this cmd is available on the path of the environment.
    env_name : str or None
        Name of the conda environment to check. If it is None, check in the
        current environment.

    Return
    """
    def raise_import_error(output):
        raise ImportError(
            f'Could not find {cmd_name} on the path of conda env {env_name}\n'
            f'{output}'
        )
    _run_shell_in_conda_env(
        CHECK_SHELL_CMD_EXISTS.format(cmd_name=cmd_name),
        env_name=env_name, raise_on_error=raise_import_error
    )

    def run_shell_cmd(*args):
        cmd_args = " ".join(args)
        _run_shell_in_conda_env(
            f"{cmd_name} {cmd_args}", env_name=env_name, raise_on_error=True
        )

    return run_shell_cmd


def get_benchmark_objective(benchmark_dir):
    """Load the objective function defined in the given benchmark.

    Parameters
    ----------
    benchmark_dir : str or Path
        The path to the folder containing the benchmark.

    Returns
    -------
    obj : class
        The class defining the objective function for the benchmark.
    """
    module_filename = Path(benchmark_dir) / 'objective.py'
    if not module_filename.exists():
        raise RuntimeError("Did not find an `objective` module in benchmark.")

    return _load_class_from_module(module_filename, "Objective")


def _list_benchmark_classes(benchmark_dir, class_name):
    """Load all classes with the same name from a benchmark's subpackage.

    Parameters
    ----------
    benchmark_dir : str or Path
        The path to the folder containing the benchmark.
    class_name : str
        Base name of the classes to load.

    Returns
    -------
    classes : List of class
        A list with all the classes with base_class_name `class_name` in the
        given subpkg of the benchmark.
    """

    classes = []
    # List all available module in benchmark.subpkg
    package = Path(benchmark_dir) / f'{class_name.lower()}s'
    submodule_files = package.glob('*.py')
    for module_filename in submodule_files:
        # Get the class
        classes.append(_load_class_from_module(module_filename, class_name))

    classes.sort(key=lambda c: c.name.lower())
    return classes


def list_benchmark_solvers(benchmark_dir):
    """List all available solver classes for a given benchmark_dir"""
    return _list_benchmark_classes(benchmark_dir, 'Solver')


def list_benchmark_datasets(benchmark_dir):
    """List all available dataset classes for a given benchmark_dir"""
    return _list_benchmark_classes(benchmark_dir, 'Dataset')


def _check_name_lists(*name_lists):
    """Normalize name_list ot a list of lowercase str."""
    res = []
    for name_list in name_lists:
        if name_list is None:
            continue
        res.extend([str(name).lower() for name in name_list])
    return res


def is_matched(name, include_patterns=None):
    """Check if a certain name is matched by any pattern in include_patterns.

    When include_patterns is None or [], always return True.
    """
    if include_patterns is None or len(include_patterns) == 0:
        return True
    name = str(name)
    for p in include_patterns:
        p = p.replace("*", '.*')
        if re.match(f".*{p}.*", name, flags=re.IGNORECASE) is not None:
            return True
    return False


def _install_required_classes(classes, include_patterns, force_patterns=None,
                              env_name=None):
    """Install all classes that are required for the run."""
    # Merge force install and install patterns.
    include_patterns = _check_name_lists(include_patterns, force_patterns)

    # Try to install all classes matching one of the patterns
    success = True
    for klass in classes:
        for klass_parameters in product_param(klass.parameters):
            name = klass._get_parametrized_name(**klass_parameters)
            if is_matched(name, include_patterns):
                force = (
                    force_patterns is not None and len(force_patterns) > 0
                    and is_matched(name, force_patterns)
                )
                success &= klass.install(env_name=env_name, force=force)

    # If one failed, raise a warning to explain how to see the install errors.
    if not success:
        warnings.warn(
            "Some solvers were not successfully installed, and will thus be "
            "ignored. Use 'export BENCHO_RAISE_INSTALL_ERROR=true' to "
            "stop at any installation failure and print the traceback.",
            UserWarning
        )


def install_required_solvers(benchmark, solver_names, forced_solvers=None,
                             env_name=None):
    """List all solvers and install the required ones."""
    solvers = list_benchmark_solvers(benchmark)
    _install_required_classes(
        solvers, solver_names, force_patterns=forced_solvers,
        env_name=env_name
    )


def install_required_datasets(benchmark, dataset_names, env_name=None):
    """List all datasets and install the required ones."""
    datasets = list_benchmark_datasets(benchmark)
    _install_required_classes(datasets, dataset_names, env_name=env_name)


class safe_import_context:
    """Do not fail on ImportError and catch import warnings"""

    def __init__(self):
        self.failed_import = False
        self.record = warnings.catch_warnings(record=True)

    def __enter__(self):
        # Catch the import warning except if install errors are raised.
        if not RAISE_INSTALL_ERROR:
            self.record.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, tb):

        silence_error = False

        # prevent import error from propagating and tag
        if exc_type is not None and issubclass(exc_type, ImportError):
            self.failed_import = True
            self.import_error = exc_type, exc_value, tb

            # Prevent the error propagation
            silence_error = True

        if not RAISE_INSTALL_ERROR:
            self.record.__exit__(exc_type, exc_value, tb)

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
