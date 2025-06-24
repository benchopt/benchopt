import sys
import warnings
import importlib
import importlib.util

from importlib.abc import Loader, MetaPathFinder
from pathlib import Path
from unittest.mock import Mock

from joblib.externals import cloudpickle

from ..config import RAISE_INSTALL_ERROR


MOCK_ALL_IMPORT = False
BENCHMARK_DIR = None
PACKAGE_NAME = "benchmark_utils"


class MockLoader(Loader):
    def __init__(self, name):
        self.name = name

    def create_module(self, spec):
        return Mock(name=self.name)

    def exec_module(self, module):
        module.__path__ = []


class MockFinder(MetaPathFinder):
    def __init__(self):
        self.specs = list()
        self.has_failed_import = False
        self._import_errors = []
        self._top_level_import = None

    def find_spec(self, fullname, path, target=None):
        """
        MockFinder is inserted at the first place of the finders list,
        so it is the first finder called by Python.
        The aim is to check if we can import the module {fullname},
        if not, we mock it. If we try to import the module {fullname}
        to check ImportError or ModuleNotFoundError,
        the mock finder will be called again that's why we
        store {fullname} in {self.specs} list
        to skip the mock finder and check if the other finders throw errors.

        Parameters
        ----------
        fullname
        path
        target

        Returns
        -------
        None or a spec if the module is mocked
        """
        if fullname in self.specs:
            return None

        # Mock all imports if MOCK_ALL_IMPORT is True
        if MOCK_ALL_IMPORT:
            return importlib.util.spec_from_loader(
                fullname, MockLoader(fullname)
            )

        # Otherwise, only mock the top level import when a failure occurs.
        try:
            # Only mock the top level import in safe_import_context,
            # to avoid edge effects with internal libraries imports.
            if self._top_level_import is None:
                self._top_level_import = fullname
                sys.meta_path.remove(self)

            self.specs.append(fullname)
            # Check if we can import the module {fullname}
            importlib.import_module(fullname)

            # If the module can be imported, we let other finders to import it,
            # so we return None
            return None
        except Exception as e:
            if RAISE_INSTALL_ERROR:
                self.has_failed_import = True
                raise e

            # Log the error and mock the import object
            self._import_errors.append((fullname, sys.exc_info()))
            return importlib.util.spec_from_loader(
                fullname, MockLoader(fullname)
            )
        finally:
            if self._top_level_import == fullname:
                self._top_level_import = None
                sys.meta_path.insert(0, self)


def mock_all_import():
    global MOCK_ALL_IMPORT
    MOCK_ALL_IMPORT = True


def _unmock_import():
    """Helper to reenable imports in tests."""
    global MOCK_ALL_IMPORT
    MOCK_ALL_IMPORT = False


def set_benchmark_module(benchmark_dir):
    global BENCHMARK_DIR
    BENCHMARK_DIR = Path(benchmark_dir)
    # add PACKAGE_NAME as a module if it exists:
    module_file = Path(benchmark_dir) / PACKAGE_NAME / '__init__.py'
    if module_file.exists():
        spec = importlib.util.spec_from_file_location(
            PACKAGE_NAME, module_file
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[PACKAGE_NAME] = module
        spec.loader.exec_module(module)
        cloudpickle.register_pickle_by_value(module)
    elif module_file.parent.exists():
        warnings.warn(
            "Folder `benchmark_utils` exists but is missing `__init__.py`. "
            "Make sure it is a proper module to allow importing from it.",
            ImportWarning
        )


class safe_import_context:
    """Context used to manage import in benchmarks.

    This context allows to avoid errors on ImportError, to be able to report
    that a solver/dataset is not installed.

    Moreover, this context also allows to mock the import when simply listing
    all solvers, for benchmark's installation or auto completion. Note that all
    costly imports should be protected with this import for benchopt to perform
    best.

    Finally, this context also catches import warnings.
    """

    def __init__(self):
        self.errors = []
        self.failed_import = False

        self.record = warnings.catch_warnings(record=True)
        self._benchmark_dir = BENCHMARK_DIR
        self._mock_finder = MockFinder()

    def __enter__(self):
        # Mock import to speed up import
        sys.meta_path.insert(0, self._mock_finder)

        # Catch the import warning except if install errors are raised.
        if not RAISE_INSTALL_ERROR:
            self.record.__enter__()

        return self

    def __exit__(self, exc_type, exc_value, tb):
        if self._mock_finder.has_failed_import:
            self.failed_import = True
            self.errors = self._mock_finder._import_errors

        if self._mock_finder in sys.meta_path:
            sys.meta_path.remove(self._mock_finder)

        if not RAISE_INSTALL_ERROR:
            self.record.__exit__(exc_type, exc_value, tb)
