import re
import click
import warnings
import itertools
from pathlib import Path

from .config import get_setting
from .base import BaseSolver, BaseDataset

from .utils.safe_import import set_benchmark_module
from .utils.dynamic_modules import _load_class_from_module
from .utils.dependencies_mixin import DependenciesMixin
from .utils.parametrized_name_mixin import product_param
from .utils.parametrized_name_mixin import ParametrizedNameMixin

from .utils.terminal_output import colorify
from .utils.terminal_output import GREEN, YELLOW

from .utils.conda_env_cmd import install_in_conda_env
from .utils.conda_env_cmd import shell_install_in_conda_env
from .utils.shell_cmd import _run_shell_in_conda_env

# Get config values
from .config import RAISE_INSTALL_ERROR


# Global variable to access the benchmark currently running globally
_RUNNING_BENCHMARK = None

# Constant to name cache directory and folder of slurm outputs
CACHE_DIR = '__cache__'
SLURM_JOB_NAME = 'benchopt_run'


MISSING_DEPS_MSG = (
    "This is probably due to missing dependency specification. The "
    "dependencies should be specified in the `requirements` class attribute.\n"
    "Examples:\n"
    "   requirements = ['pkg'] # conda package `pkg`\n"
    "   requirements = ['chan::pkg'] # package `pkg` in conda channel `chan`\n"
    "   requirements = ['pip::pkg'] # PyPi package `pkg`"
)

SUBSTITUTIONS = {"*": ".*"}


def get_running_benchmark():
    """Return the benchmark currently running."""
    return _RUNNING_BENCHMARK


class Benchmark:
    """Benchmark exposes all constituents of the benchmark folder.

    Parameters
    ----------
    benchmark_dir : str or Path-like
        Folder containing the benchmark. The folder should at least
        contain an `objective.py` file defining the `Objective`
        function for the benchmark.
    allow_meta_from_json : bool
        If set to True, allow the object to be instanciated even when
        objective.py cannot be found. In this case, the metadata are retrieved
        from the benchmark_meta.json file. This should only be used to generate
        HTML pages with results.

    Attributes
    ----------
    mem : joblib.Memory
        Caching mechanism for the benchmark.
    """
    def __init__(
        self, benchmark_dir, allow_meta_from_json=False,
    ):
        self.benchmark_dir = Path(benchmark_dir)

        global _RUNNING_BENCHMARK
        _RUNNING_BENCHMARK = self
        set_benchmark_module(self.benchmark_dir)

        # Load the benchmark metadat defined in `objective.py` or
        # in `benchmark_meta.json`.
        try:
            objective = self.get_benchmark_objective()
            self.pretty_name = objective.name
            self.url = getattr(objective, "url", None)
            self.min_version = getattr(objective, 'min_benchopt_version', None)
        except RuntimeError:
            if not allow_meta_from_json:
                raise click.BadParameter(
                    f"The folder '{benchmark_dir}' does not contain "
                    "`objective.py`.\nMake sure you provide the path to a "
                    "valid benchmark."
                )
            meta_data = (self.benchmark_dir / "benchmark_meta.json")
            if not meta_data.exists():
                raise FileNotFoundError(
                    "Can't find objective.py or benchmark_meta.json to get "
                    "benchmark info for the html_generation."
                )

            with meta_data.open() as f:
                import json
                meta = json.load(f)
                self.pretty_name = meta["pretty_name"]
                self.url = meta.get("url", None)

        if self.url is None:
            self.name = self.benchmark_dir.resolve().name
            self.url = f"https://github.com/benchopt/{self.name}"
        else:
            self.name = Path(self.url).name
        # replace dots to avoid issues with `with_suffix``
        self.name = self.name.replace('.', '-')

    ####################################################################
    # Helpers to access and validate objective, solvers and datasets
    ####################################################################

    def get_benchmark_objective(self):
        """Load the objective function defined in the given benchmark.

        Returns
        -------
        objective_class : class
            The class defining the objective function for the benchmark.
        """
        module_filename = self.benchmark_dir / 'objective.py'
        if not module_filename.exists():
            raise RuntimeError(
                "Did not find an `objective` module in benchmark."
            )

        return _load_class_from_module(
            module_filename, "Objective", benchmark_dir=self.benchmark_dir
        )

    def check_objective_filters(self, objective_filters):
        "Check that the patterns are valid and return selected configurations."
        return _check_patterns(
            [self.get_benchmark_objective()], objective_filters,
            name_type="objective"
        )

    def get_solvers(self):
        "List all available solver classes for the benchmark."
        return self._list_benchmark_classes(BaseSolver)

    def get_solver_names(self):
        "List all available solver names for the benchmark."
        return [s.name for s in self.get_solvers()]

    def check_solver_patterns(self, solver_patterns, class_only=False):
        "Check that the patterns are valid and return selected configurations."
        return _check_patterns(
            self.get_solvers(), solver_patterns, name_type='solver',
            class_only=class_only
        )

    def get_datasets(self):
        "List all available dataset classes for the benchmark."
        return self._list_benchmark_classes(BaseDataset)

    def get_dataset_names(self):
        "List all available dataset names for the benchmark."
        return [d.name for d in self.get_datasets()]

    def check_dataset_patterns(self, dataset_patterns, class_only=False):
        "Check that the patterns are valid and return selected configurations."
        return _check_patterns(
            self.get_datasets(), dataset_patterns, name_type='dataset',
            class_only=class_only
        )

    def _list_benchmark_classes(self, base_class):
        """Load all classes with the same name from a benchmark's subpackage.

        Parameters
        ----------
        base_class : class
            Base class for the classes to load.

        Returns
        -------
        classes : List of class
            A list with all the classes with base_class in the given subpkg of
            the benchmark.
        """

        classes = []
        # List all available module in benchmark.subpkg
        class_name = base_class.__name__.replace('Base', '')
        package = self.benchmark_dir / f'{class_name.lower()}s'
        submodule_files = package.glob('[!.]*.py')
        for module_filename in submodule_files:
            if module_filename.name.startswith("template_"):
                # skip template solvers and datasets
                continue
            # Get the class
            try:
                cls = _load_class_from_module(
                    module_filename, class_name,
                    benchmark_dir=self.benchmark_dir
                )
                if not issubclass(cls, base_class):
                    warnings.warn(colorify(
                        f"class {cls.__name__} in {module_filename} is not a "
                        f"subclass from base class benchopt."
                        f"{base_class.__name__}", YELLOW
                    ))

            except Exception:

                import traceback
                tb_to_print = traceback.format_exc(chain=False)

                class FailedImport(ParametrizedNameMixin, DependenciesMixin):
                    "Object for the class list that raises error if used."

                    name = get_failed_import_object_name(
                        module_filename, class_name
                    )

                    @classmethod
                    def is_installed(cls, **kwargs):
                        print(
                            f"Failed to import {class_name} from "
                            f"{module_filename}. Please fix the following "
                            "error to use this file with benchopt:\n"
                            f"{tb_to_print}"
                        )
                        return False

                cls = FailedImport
            classes.append(cls)

        classes.sort(key=lambda c: c.name.lower())
        return classes

    #####################################################
    # Access to output files for the benchmark
    #####################################################

    def get_output_folder(self):
        """Get the folder to store the output of the benchmark.

        If it does not exists, create it.
        """
        output_dir = self.benchmark_dir / "outputs"
        output_dir.mkdir(exist_ok=True)
        return output_dir

    def get_slurm_folder(self):
        """Get the folder to store the output of the slurm executor."""
        slurm_dir = self.benchmark_dir / SLURM_JOB_NAME
        return slurm_dir

    def get_result_file(self, filename=None):
        """Get a result file from the benchmark.

        Parameters
        ----------
        filename : str
            Select a specific file from the benchmark. If None, this will
            select the most recent result file in the benchmark output folder.
        """
        # List all result files
        output_folder = self.get_output_folder()
        all_result_files = list(
            output_folder.glob("*.parquet")
        ) + list(output_folder.glob("*.csv"))
        all_result_files = sorted(
            all_result_files, key=lambda t: t.stat().st_mtime
        )

        if filename is not None and filename != 'all':
            result_path = (output_folder / filename)
            result_filename = result_path.with_suffix('.parquet')

            if not result_filename.exists():
                result_filename = result_path.with_suffix('.csv')

            if not result_filename.exists():
                if Path(filename).exists():
                    result_filename = Path(filename)
                else:
                    all_result_files = '\n- '.join([
                        str(s) for s in all_result_files
                    ])
                    raise FileNotFoundError(
                        f"Could not find result file {filename}. Available "
                        f"result files are:\n- {all_result_files}"
                    )
        else:
            if len(all_result_files) == 0:
                raise RuntimeError(
                    "Could not find any Parquet nor "
                    f"CSV result files in {output_folder}."
                )
            result_filename = all_result_files[-1]
            if filename == 'all':
                result_filename = all_result_files

        if isinstance(result_filename, list):
            is_csv_file = any(fname.suffix == ".csv"
                              for fname in result_filename)
        else:
            is_csv_file = result_filename.suffix == ".csv"

        if is_csv_file:
            print(colorify(
                "WARNING: CSV files are deprecated."
                "Please use Parquet files instead.",
                YELLOW
            ))

        return result_filename

    #####################################################
    # Caching mechanism
    #####################################################

    @property
    def mem(self):
        from joblib import Memory
        if not hasattr(self, '_mem'):
            self._mem = Memory(location=self.get_cache_location(), verbose=0)
        return self._mem

    def get_cache_location(self):
        "Get the location for the cache of the benchmark."
        benchopt_cache_dir = get_setting("cache")
        if benchopt_cache_dir is None:
            return self.benchmark_dir / CACHE_DIR

        return Path(benchopt_cache_dir) / self.name

    def cache(self, func, force=False, ignore=None, collect=False):
        """Create a cached function for the given function.

        A special behavior is enforced for the 'force' kwargs. If it is present
        and True, the function will always be recomputed.

        If the collect flag is set to True, the function will return the result
        if it exists, or None if it does not. This is useful to gather results
        that are already in cache.
        """

        # Create a cached version of `func` and handle cases where we force
        # the run.
        func_cached = self.mem.cache(func, ignore=ignore)
        if force:
            assert not collect, "Cannot collect and force computation."

            def _func_cached(**kwargs):
                return func_cached.call(**kwargs)[0]
        elif collect:
            def _func_cached(**kwargs):
                assert not kwargs.get('force', False), (
                    "Cannot collect and force computation."
                )
                if func_cached.check_call_in_cache(**kwargs):
                    return func_cached(**kwargs)
                return None
        else:
            def _func_cached(**kwargs):
                if kwargs.get('force', False):
                    return func_cached.call(**kwargs)[0]
                return func_cached(**kwargs)

        return _func_cached

    #####################################################
    # Configuration and settings for the benchmark
    #####################################################

    def get_config_file(self):
        "Get the location for the config file of the benchmark."
        yml_path = self.benchmark_dir / "config.yml"
        return yml_path

    def get_setting(self, setting_name, default_config=None):
        "Retrieve the setting value from benchmark config."

        # Get the config file and read it
        config_file = self.get_config_file()
        return get_setting(
            name=setting_name, config_file=config_file,
            benchmark_name=self.name, default_config=default_config
        )

    def get_test_config_file(self):
        """Get the location for the test config file for the benchmark.

        This file will be used to check if a test should be xfailed/skipped on
        specific solvers and platforms when we have installation or running
        issues. Returns None if this file does not exists.
        """
        test_config_file = self.benchmark_dir / 'test_config.py'
        if not test_config_file.exists():
            return None
        return test_config_file

    #####################################################
    # Install and run helpers
    #####################################################

    def install_all_requirements(self, include_solvers, include_datasets,
                                 minimal=False, env_name=None,
                                 force=False, quiet=False, download=False):
        """Install all classes that are required for the run.

        Parameters
        ----------
        include_solvers : list of BaseSolver
            patterns to select solvers to install.
        include_datasets : list of BaseDataset
            patterns to select datasets to install.
        minimal : bool (default: False)
            only install requirements for the objective function.
        env_name : str or None (default: None)
            Name of the conda env where the class should be installed. If
            None, tries to install it in the current environment.
        force : bool (default: False)
            If set to True, forces reinstallation when using conda.
        quiet : bool (default: False)
            If True, silences the output of install commands.
        download : bool (default: False)
            If True, make sure the data are downloaded on the computer.
        """
        # Collect all classes matching one of the patterns
        print("Collecting packages...", end='', flush=True)

        check_installs, missings = [], []
        objective = self.get_benchmark_objective()
        conda_reqs, shell_install_scripts, post_install_hooks, missing_deps = (
            objective.collect(env_name=env_name, force=force)
        )
        if missing_deps:
            raise AttributeError(
                "Could not find dependencies in objective.py while it is not "
                f"importable. {MISSING_DEPS_MSG}"
            )

        if len(shell_install_scripts) > 0 or len(conda_reqs) > 0:
            check_installs += [objective]
        to_install = itertools.chain(include_datasets, include_solvers)
        if not minimal:
            for klass in to_install:
                reqs, scripts, hooks, missing = (
                    klass.collect(env_name=env_name, force=force)
                )
                # If a class is not importable but has no requirements,
                # it might be because the requirements are specified
                # as global ones in the Objective. Otherwise, raise a
                # comprehensible error.
                if missing is not None:
                    missings.append(missing)

                conda_reqs += reqs
                shell_install_scripts += scripts
                post_install_hooks += hooks
                if len(scripts) > 0 or len(reqs) > 0:
                    check_installs += [klass]
            print(colorify(' done', GREEN))

        # Install the collected requirements
        list_install = '\n'.join([
            f"- {klass.name}" for klass in check_installs
        ])
        if len(list_install) == 0:
            self.check_missing(missings)
            print("All required solvers are already installed.")
            if download:
                self.download_all_data(include_datasets, env_name, quiet)
            return

        print(f"Installing required packages for:\n{list_install}\n...",
              end='', flush=True)
        install_in_conda_env(
            *list(set(conda_reqs)), env_name=env_name, force=force,
            quiet=quiet
        )
        for install_script in shell_install_scripts:
            shell_install_in_conda_env(
                install_script, env_name=env_name, quiet=quiet
            )
        for hooks in post_install_hooks:
            hooks(env_name=env_name)
        print(colorify(' done', GREEN))

        # Check install for all classes that needed extra requirements
        print('- Checking installed packages...', end='', flush=True)
        not_installed = set()
        for klass in set(check_installs + missings):
            cls_success = klass.is_installed(env_name=env_name)
            if cls_success and klass in missings:
                # This class only depends on global requirements
                missings.remove(klass)
            elif not cls_success:
                not_installed.add(klass.name)

        self.check_missing(missings)

        # If one failed, raise a warning to explain how to see the install
        # errors.
        if len(not_installed) == 0:
            print(colorify(' done', GREEN))
        else:
            warnings.warn(
                "Some solvers were not successfully installed, and will thus "
                "be ignored. Use 'export BENCHOPT_RAISE_INSTALL_ERROR=true' to"
                " stop at any installation failure and print the traceback.",
                UserWarning
            )
            print(colorify(f" done (missing deps: {not_installed})", YELLOW))

        if download:
            self.download_all_data(include_datasets, env_name, quiet)

    def download_all_data(self, datasets, env_name, quiet):
        if len(datasets) == 0:
            return
        cmd = f"benchopt check-data {self.benchmark_dir} -d "
        cmd += "-d ".join(d.name for d in datasets)
        _run_shell_in_conda_env(
            cmd, env_name=env_name, raise_on_error=True, capture_stdout=False
        )

    def check_missing(self, missings):
        # Check that classes not importable, with no requirements, only depends
        # on global requirements specified in Objective.requirements.
        # Otherwise, we raise a comprehensible error.
        if len(missings) > 0:
            # Format the list of classes missing requirements.
            cls_types = {'Solver': [], 'Dataset': []}
            for klass in missings:
                cls_type = klass.__base__.__name__.replace("Base", "")
                cls_types[cls_type].append(klass.name)
            cls_types = {
                k: f'{cls_type}\n' + '\n'.join([f'- {c}' for c in v])
                for k, v in cls_types.items() if len(v) > 0
            }
            missing_cls = '\n'.join(cls_types.values())

            raise AttributeError(
                f"Could not find dependencies for the following classes while "
                f"they are not importable:\n{missing_cls}\n{MISSING_DEPS_MSG}"
            )

    def get_all_runs(self, solvers=None, forced_solvers=None,
                     datasets=None, objectives=None, output=None):
        """Generator with all combinations to run for the benchmark.

        Parameters
        ----------
        solvers : list | None
            List of solvers to include in the benchmark. If None
            all solvers available are run.
        forced_solvers : list | None
            List of solvers to include in the benchmark and for
            which one forces recomputation.
        datasets : list | None
            List of datasets to include. If None all available
            datasets are used.
        objectives : list | None
            Filters to select specific objective parameters. If None,
            all objective parameters are tested
        output : TerminalOutput or None
            Object to manage the output in the terminal.

        Yields
        ------
        dataset : BaseDataset instance
        objective : BaseObjective instance
        solver : BaseSolver instance
        force : bool
        """
        all_datasets = _list_parametrized_classes(*datasets)
        all_solvers, solvers_buffer = buffer_iterator(
            _list_parametrized_classes(*solvers)
        )
        for dataset, is_installed in all_datasets:
            output.set(dataset=dataset)
            if not is_installed:
                output.show_status('not installed', dataset=True)
                continue
            output.display_dataset()
            all_objectives = _list_parametrized_classes(
                *objectives, check_installed=False
            )
            for objective, is_installed in all_objectives:
                output.set(objective=objective)
                if not is_installed:
                    output.show_status('not installed', objective=True)
                    continue
                output.display_objective()
                for i_solver, (solver, is_installed) in enumerate(all_solvers):
                    output.set(solver=solver, i_solver=i_solver)

                    if not is_installed:
                        output.show_status('not installed')
                        continue

                    force = is_matched(
                        str(solver), forced_solvers, default=False
                    )
                    yield dict(
                        dataset=dataset, objective=objective, solver=solver,
                        force=force, output=output.clone()
                    )
                all_solvers = solvers_buffer


def _check_name_lists(*name_lists):
    "Normalize name_list to a list of string."
    res = []
    for name_list in name_lists:
        if name_list is None:
            continue
        res.extend([str(name) for name in name_list])
    return res


def is_matched(name, include_patterns=None, default=True):
    """Check if a certain name is matched by any pattern in include_patterns.

    When include_patterns is None or [], always return `default`.
    """
    if include_patterns is None or len(include_patterns) == 0:
        return default
    name = str(name)
    name = _extract_options(name)[0]
    for p in include_patterns:
        p = _extract_options(p)[0]
        for old, new in SUBSTITUTIONS.items():
            p = p.replace(old, new)
        if re.match(f"^{p}$", name, flags=re.IGNORECASE) is not None:
            return True
    return False


def _extract_options(name):
    """Remove options indicated within '[]' from a name.

    Parameters
    ----------
    name : str
        Input name.

    Returns
    -------
    basename : str
        Name without options.
    args : list
        List of unnamed options.
    kwargs : dict()
        Dictionary with options.

    Examples
    --------
    >>> _extract_options("foo")  # "foo", [], dict()
    >>> _extract_options("foo[bar=2]")  # "foo", [], dict(bar=2)
    >>> _extract_options("foo[baz]")  # "foo", ["baz"], dict()
    """
    if name.count("[") != name.count("]"):
        raise ValueError(f"Invalid name (missing bracket): {name}")

    basename = "".join(re.split(r"\[.*\]", name))
    matches = re.findall(r"\[.*\]", name)

    if len(matches) == 0:
        return basename, [], {}
    elif len(matches) > 1:
        raise ValueError(f"Invalid name (multiple brackets): {name}")
    else:
        match = matches[0]
        match = match[1:-1]  # remove brackets

        result = _extract_parameters(match)
        if isinstance(result, dict):
            return basename, [], result
        elif isinstance(result, list):
            return basename, result, {}
        else:
            raise ValueError(
                f"Impossible. Please report this bug.\n"
                f"_extract_parameters returned '{result}'"
            )


def _extract_parameters(string):
    """Extract parameters from a string.

    If the string contains a "=", returns a dict, otherwise returns a list.

    Examples
    --------
    >>> _extract_parameters("foo")  # ["foo"]
    >>> _extract_parameters("foo, 42, True")  # ["foo", 42, True]
    >>> _extract_parameters("foo=bar")  # {"foo": "bar"}
    >>> _extract_parameters("foo=[bar, baz]")  # {"foo": ["bar", "baz"]}
    >>> _extract_parameters("foo=1, baz=True")  # {"foo": 1, "baz": True}
    >>> _extract_parameters("'foo, bar'=[(0, 1),(1, 0)]")
    >>> # {"foo, bar": [(0, 1),(1, 0)]}
    """
    import ast
    original = string

    # First, replace some expressions with their hashes, to avoid modification:
    # - quoted names
    all_matches = re.findall(r"'[^'\"]*'", string)
    all_matches += re.findall(r'"[^\'"]*"', string)
    # - numbers of the form "1e-3" (but not names like "foo1e3")
    all_matches += re.findall(
        r"(?<![a-zA-Z0-9_])[+-]?[0-9]+[.]?[0-9]*[eE][-+]?[0-9]+", string)
    for match in all_matches:
        string = string.replace(match, str(hash(match)))

    # Second, add quotes to all variable names (foo -> 'foo').
    # Accepts dots and dashes within names.
    string = re.sub(r"[a-zA-Z][a-zA-Z0-9._-]*", r"'\g<0>'", string)

    # Third, change back the hashes to their original names.
    for match in all_matches:
        string = string.replace(str(hash(match)), match)

    # Prepare the sequence for AST parsing.
    # Sequences with "=" are made into a dict expression {'foo': 'bar'}.
    # Sequences without "=" are made into a list expression ['foo', 'bar'].
    if "=" in string:
        string = "{" + string.replace("=", ":") + "}"
    else:
        string = "[" + string + "]"

    # Remove quotes for python language tokens
    for token in ["True", "False", "None"]:
        string = string.replace(f'"{token}"', token)
        string = string.replace(f"'{token}'", token)

    # Evaluate the string.
    try:
        return ast.literal_eval(string)
    except (ValueError, SyntaxError):
        raise ValueError(f"Invalid name '{original}', evaluated as {string}.")


def _check_patterns(all_classes, patterns, name_type='dataset',
                    class_only=False):
    """Check the patterns and return a list of selected classes and params.

    Raise an error if a pattern does not match any dataset name,
    or if a parameter does not appear as a class parameter.

    Parameters
    ----------
    all_classes: list of ParametrizedNameMixin
        The possible classes to select from.
    patterns: list of str | dict
        List of patterns to select the classes. These patterns can be either:
            - str with the class name and parameters values:
                "cls_name[params1=[...],params2=...]"
            - dict with keys as cls_name and a dictionary of parameter values.
                {'cls_name': dict(params1=[...], params2=[])}
    name_type: str
        Used to raise sensible error depending on the type of classes which
        are selected.
    class_only: bool
        Only return the classes that are matched, without a list of parameters.

    Returns
    -------
    selected_classes: list of (ParametrizedNameMixin, parameters dict)
        A list with 2-tuple containing the selected class and a dictionary
        with selected parameters for this class.
    """
    # If no patterns is provided or all is provided, return all the classes.
    if (patterns is None or len(patterns) == 0
            or any(p == 'all' for p, *_ in patterns)):
        all_valid_patterns = [(cls, cls.parameters) for cls in all_classes]
        if not class_only:
            return all_valid_patterns
        return set(cls for cls, _ in all_valid_patterns)

    # Patterns can be either str or dict. Convert everything to 3-tuple with
    # (cls_name, args, kwargs). cls_name and kwargs correspond to class and
    # parameters selector. args is used to allow passing directly a list when
    # the class have only one parameter.
    def preprocess_patterns(pattern):
        if isinstance(pattern, str):
            return [_extract_options(pattern)]
        if isinstance(pattern, dict):
            return [
                (name, options, {}) if isinstance(options, list)
                else (name, [], options)
                for name, options in pattern.items()]
        raise TypeError()
    patterns = [p for q in patterns for p in preprocess_patterns(q)]

    # Check that the provided patterns match at least one dataset and pair the
    # matching clas with the selector.
    matched, invalid_patterns = [], []
    for p, args, kwargs in patterns:
        matched += [
            (cls, (args, kwargs))
            for cls in all_classes
            if is_matched(cls.name, [p])
        ]
        if len(matched) == 0:
            invalid_patterns.append(p)

    # If some patterns did not matched any class, raise an error
    if len(invalid_patterns) > 0:
        all_names = '- ' + '\n- '.join(cls.name for cls in all_classes)
        raise click.BadParameter(
            f"Patterns {invalid_patterns} did not match any {name_type}.\n"
            f"Available {name_type}s are:\n{all_names}"
        )

    # Check that the parameters are well formated:
    # - not ambiguous nor duplicated
    # - parameters correspond to existing one for a given class.
    all_valid_patterns = []
    for cls, (args, kwargs) in matched:
        param_names = [p.strip() for k in cls.parameters for p in k.split(',')]
        if len(args) != 0:
            if len(cls.parameters) > 1:
                raise ValueError(
                    f"Ambiguous positional parameter for {cls.name}."
                )
            elif len(kwargs) > 0:
                raise ValueError(
                    f"Both positional and keyword parameters for {cls.name}."
                )
            kwargs = {list(cls.parameters.keys())[0]: args}
        else:
            bad_params = [
                p.strip() for k in kwargs for p in k.split(',')
                if p.strip() not in param_names
            ]
            if len(bad_params) > 0:
                msg = "Possible parameters are:\n- " + "\n- ".join(param_names)
                if len(param_names) == 0:
                    msg = f"This {name_type} has no parameters."
                bad_params = ', '.join(f"'{p}'" for p in bad_params)
                raise ValueError(
                    f"Unknown parameter {bad_params} for {name_type} "
                    f"{cls.name}.\n{msg}"
                )
        params = cls.parameters.copy()
        params.update(kwargs)
        all_valid_patterns.append((cls, params))

    if not class_only:
        return all_valid_patterns

    return set(cls for cls, _ in all_valid_patterns)


def _list_parametrized_classes(*classes, check_installed=True):
    """Generator with class instances for all selected parameters."""
    for klass, params in classes:
        if (check_installed and not klass.is_installed(
                raise_on_not_installed=RAISE_INSTALL_ERROR
        )):
            yield klass.name, False
            continue

        for parameters in _get_used_parameters(klass, params):
            yield klass.get_instance(**parameters), True


def _get_used_parameters(klass, params):
    """Get the list of parameters to use in the class."""
    # Make sure that all parameters are passed as iterables.
    params = {
        key: (val if isinstance(val, (list, tuple)) else [val])
        for key, val in params.items()
    }

    # Use product_param to get all combinations of parameters.
    # Then, update the default parameters (klass.parameters) with the
    # parameters extracted from filter names.
    used_parameters = []
    for update in product_param(params):
        for default in product_param(klass.parameters):
            default = default.copy()  # avoid modifying the original

            # check that all parameters are defined in klass.parameters
            for key in update:
                if key not in default:
                    raise ValueError(
                        f"Unknown parameter '{key}', parameter must be in "
                        f"{list(default.keys())}")

            default.update(update)
            if default not in used_parameters:  # avoid duplicates
                used_parameters.append(default)

    return used_parameters


def buffer_iterator(it):
    """Buffer the output of an iterator to repeat it without recomputing."""
    buffer = []

    def buffered_it(buffer):
        for val in it:
            buffer.append(val)
            yield val

    return buffered_it(buffer), buffer


def get_failed_import_object_name(module_file, cls_name):
    # Parse the module file to find the name of the failing object

    import ast
    module_ast = ast.parse(Path(module_file).read_text())
    classdef = [
        c for c in module_ast.body
        if isinstance(c, ast.ClassDef) and c.name == cls_name
    ]
    if len(classdef) == 0:
        raise ValueError(f"Could not find {cls_name} in module {module_file}.")
    c = classdef[-1]
    name_assign = [
        a for a in c.body
        if (isinstance(a, ast.Assign) and any(list(
            (isinstance(t, ast.Name) and t.id == "name") for t in a.targets
        )))
    ]
    if len(name_assign) == 0:
        raise ValueError(
            f"Could not find {cls_name} name in module {module_file}"
        )
    return name_assign[-1].value.value
