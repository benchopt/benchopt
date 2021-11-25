import re
import click
import warnings
from pathlib import Path

from .config import get_setting
from .base import BaseSolver, BaseDataset
from .utils.colorify import colorify, YELLOW
from .utils.dynamic_modules import _load_class_from_module
from .utils.parametrized_name_mixin import product_param
from .utils.parametrized_name_mixin import _list_all_parametrized_names

from .utils.conda_env_cmd import install_in_conda_env
from .utils.conda_env_cmd import shell_install_in_conda_env


CACHE_DIR = '__cache__'


class Benchmark:
    def __init__(self, benchmark_dir):
        self.benchmark_dir = Path(benchmark_dir)
        self.name = self.benchmark_dir.resolve().name

        try:
            self.get_benchmark_objective()
        except RuntimeError:
            raise click.BadParameter(
                f"The folder '{benchmark_dir}' does not contain "
                "`objective.py`.\nMake sure you provide the path to a valid "
                "benchmark."
            )

    @property
    def mem(self):
        from joblib import Memory
        if not hasattr(self, '_mem'):
            self._mem = Memory(location=self.get_cache_location(), verbose=0)
        return self._mem

    def get_setting(self, setting_name):
        "Retrieve the setting value from benchmark config."

        # Get the config file and read it
        config_file = self.get_config_file()
        return get_setting(name=setting_name, config_file=config_file,
                           benchmark_name=self.name)

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

        return _load_class_from_module(module_filename, "Objective")

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
        submodule_files = package.glob('*.py')
        for module_filename in submodule_files:
            # Get the class
            cls = _load_class_from_module(module_filename, class_name)
            if issubclass(cls, base_class):
                classes.append(cls)
            else:
                print(colorify(
                    f"WARNING: class {cls} in {module_filename} does not "
                    f"derive from base class {base_class}", YELLOW
                ))

        classes.sort(key=lambda c: c.name.lower())
        return classes

    def get_solvers(self):
        "List all available solver classes for the benchmark."
        return self._list_benchmark_classes(BaseSolver)

    def get_solver_names(self):
        "List all available solver names for the benchmark."
        return [s.name for s in self._list_benchmark_classes(BaseSolver)]

    def get_datasets(self):
        "List all available dataset classes for the benchmark."
        return self._list_benchmark_classes(BaseDataset)

    def get_dataset_names(self):
        "List all available dataset names for the benchmark."
        return [d.name for d in self._list_benchmark_classes(BaseDataset)]

    def get_cache_location(self):
        "Get the location for the cache of the benchmark."
        return self.benchmark_dir / CACHE_DIR

    def get_config_file(self):
        "Get the location for the config file of the benchmark."
        return self.benchmark_dir / 'config.ini'

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

    def get_output_folder(self):
        """Get the folder to store the output of the benchmark.

        If it does not exists, create it.
        """
        output_dir = self.benchmark_dir / "outputs"
        output_dir.mkdir(exist_ok=True)
        return output_dir

    def get_result_file(self, filename=None):
        """Get a result file from the benchmark.

        Parameters
        ----------
        filename : str
            Select a specific file from the benchmark. If None, this will
            select the most recent CSV file in the benchmark output folder.
        """
        # List all result files
        output_folder = self.get_output_folder()
        all_csv_files = output_folder.glob("*.csv")
        all_csv_files = sorted(
            all_csv_files, key=lambda t: t.stat().st_mtime
        )

        if filename is not None and filename != 'all':
            result_filename = (output_folder / filename).with_suffix('.csv')
            if not result_filename.exists():
                if Path(filename).exists():
                    result_filename = Path(filename)
                else:
                    all_csv_files = '\n- '.join([
                        str(s) for s in all_csv_files
                    ])
                    raise FileNotFoundError(
                        f"Could not find result file {filename}. Available "
                        f"result files are:\n- {all_csv_files}"
                    )
        else:
            if len(all_csv_files) == 0:
                raise RuntimeError(
                    f"Could not find any CSV result files in {output_folder}."
                )
            result_filename = all_csv_files[-1]
            if filename == 'all':
                result_filename = all_csv_files

        return result_filename

    def install_all_requirements(self, include_solvers, include_datasets,
                                 env_name=None, force=False):
        """Install all classes that are required for the run.

        Parameters
        ----------
        include_solvers : list of str
            patterns to select solvers to install.
        include_datasets : list of str
            patterns to select datasets to install.
        env_name : str or None (default: None)
            Name of the conda env where the class should be installed. If
            None, tries to install it in the current environment.
        force : boolean (default: False)
            If set to True, forces reinstallation when using conda.
        """
        # Collect all classes matching one of the patterns
        print("Collecting packages:")
        conda_reqs, shell_install_scripts, post_install_hooks = [], [], []
        check_installs = []
        for list_classes, include_patterns in [
                (self.get_solvers(), include_solvers),
                (self.get_datasets(), include_datasets)
        ]:
            include_patterns = _check_name_lists(include_patterns)
            for klass in list_classes:
                for klass_parameters in product_param(klass.parameters):
                    name = klass._get_parametrized_name(**klass_parameters)
                    if is_matched(name, include_patterns):
                        reqs, scripts, hooks = (
                            klass.collect(env_name=env_name, force=force)
                        )
                        conda_reqs += reqs
                        shell_install_scripts += scripts
                        post_install_hooks += hooks
                        if len(scripts) > 0 or len(reqs) > 0:
                            check_installs += [klass]
                        break
        print('... done')

        # Install the collected requirements
        list_install = '\n'.join([
            f"- {klass.name}" for klass in check_installs
        ])
        if len(list_install) == 0:
            print("All required solvers are already installed.")
            return
        print(f"Installing required packages for:\n{list_install}\n...",
              end='', flush=True)
        install_in_conda_env(
            *list(set(conda_reqs)), env_name=env_name, force=force
        )
        for install_script in shell_install_scripts:
            shell_install_in_conda_env(install_script, env_name=env_name)
        for hooks in post_install_hooks:
            hooks(env_name=env_name)
        print(' done')

        # Check install for all classes that needed extra requirements
        print('- Checking installed packages...', end='', flush=True)
        success = True
        for klass in check_installs:
            success |= klass.is_installed(env_name=env_name)

        # If one failed, raise a warning to explain how to see the install
        # errors.
        if not success:
            warnings.warn(
                "Some solvers were not successfully installed, and will thus "
                "be ignored. Use 'export BENCHOPT_RAISE_INSTALL_ERROR=true' to"
                " stop at any installation failure and print the traceback.",
                UserWarning
            )
        print(' done')

    def validate_dataset_patterns(self, dataset_patterns):
        "Check that all provided patterns match at least one dataset"

        # List all dataset strings.
        all_datasets = _list_all_parametrized_names(*self.get_datasets())

        _validate_patterns(all_datasets, dataset_patterns, name_type='dataset')

    def validate_solver_patterns(self, solver_patterns):
        "Check that all provided patterns match at least one solver"

        # List all dataset strings.
        all_solvers = _list_all_parametrized_names(*self.get_solvers())

        _validate_patterns(all_solvers, solver_patterns, name_type='solver')


def _check_name_lists(*name_lists):
    "Normalize name_list ot a list of lowercase str."
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
    # we use [] to signal options in patterns, we must escape them for re
    substitutions = {"*": ".*", "[": r"\[", "]": r"\]"}
    for p in include_patterns:
        for old, new in substitutions.items():
            p = p.replace(old, new)
        if re.match(f"^{p}.*", name, flags=re.IGNORECASE) is not None:
            return True
    return False


def _validate_patterns(all_names, patterns, name_type='dataset'):
    "Check that all provided patterns match at least one name."
    if patterns is None:
        return

    # Check that the provided patterns match at least one dataset.
    invalid_patterns = []
    for p in patterns:
        matched = any([is_matched(name, [p]) for name in all_names])
        if not matched:
            invalid_patterns.append(p)

    # If some patterns did not matched any dataset, raise an error
    if len(invalid_patterns) > 0:
        all_names = '- ' + '\n- '.join(all_names)
        raise click.BadParameter(
            f"Patterns {invalid_patterns} did not match any {name_type}.\n"
            f"Available {name_type}s are:\n{all_names}"
        )
