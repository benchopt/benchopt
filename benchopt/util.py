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


def _check_name_list(name_list):
    """Normalize name_list ot a list of lowercase str."""
    if name_list is None:
        return []
    return [str(name).lower() for name in name_list]


def filter_classes_on_name(classes, include=None, forced=None, exclude=None):
    """Filter a list of classes based on their name attribute.

    Parameters
    ----------
    classes: list of class
        The list to be filter. Each class should have a `name` class field.
    include: list of str
        Included name patterns.
    forced: list of str
        Second included name patterns list, used to force re-run.
    exclude: list of str
        Excluded name patterns. Inclusion patterns take precedence on this.

    Returns
    -------
    classes: list of class
        The list of class curated by the given filters.
    """

    # Currate the list of names
    exclude = _check_name_list(exclude)
    include_patterns = _check_name_list(include) + _check_name_list(forced)

    if len(exclude) > 0:
        # If a solver is explicitly included in solver_include, this takes
        # precedence over the exclusion parameter in the config file.
        exclude = set(exclude) - set(include + forced)
        classes = [c for c in classes if not is_matched(c.name, exclude)]

    if len(include_patterns) > 0:
        classes = [c for c in classes if is_matched(c.name, include_patterns)]

    return classes


def is_matched(name, include_patterns=None):
    """Check if a certain name is matched by any pattern in include_patterns.

    When include_patterns is None or [], always return True.
    """
    if include_patterns is None or len(include_patterns) == 0:
        return True
    for p in include_patterns:
        p = p.replace("*", '.*')
        if re.match(f".*{p}.*", name, flags=re.IGNORECASE) is not None:
            return True
    return False


def install_solvers(solvers, forced_solvers=None, env_name=None):
    """Install the listed solvers if needed."""

    successes = []
    for solver in solvers:
        force_install = solver.name.lower() in forced_solvers
        success = solver.install(env_name=env_name, force=force_install)
        successes.append(success)

    if not all(successes):
        warnings.warn(
            "Some solvers were not successfully installed, and will thus be "
            "ignored. Use 'export BENCHO_RAISE_INSTALL_ERROR=true' to "
            "stop at any installation failure and print the traceback.",
            UserWarning
        )


def install_required_datasets(benchmark, dataset_names, env_name=None):
    """List all datasets and install the required ons"""
    datasets = list_benchmark_datasets(benchmark)
    for dataset_class in datasets:
        for dataset_parameters in product_param(dataset_class.parameters):
            dataset = dataset_class(**dataset_parameters)
            if is_matched(str(dataset), dataset_names):
                dataset_class.install(env_name=env_name, force=False)


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
