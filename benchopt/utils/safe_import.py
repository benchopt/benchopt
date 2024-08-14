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
MOCK_FAILED_IMPORT = False
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

        try:
            if MOCK_ALL_IMPORT:
                raise ImportError

            self.specs.append(fullname)
            # Check if we can import the module {fullname}
            importlib.import_module(fullname)
            # If the module can be imported, we let other finders to import it,
            # so we return None
            return None
        except Exception:
            return importlib.util.spec_from_loader(fullname,
                                                   MockLoader(fullname))


def mock_all_import():
    global MOCK_ALL_IMPORT
    MOCK_ALL_IMPORT = True


def mock_failed_import():
    global MOCK_FAILED_IMPORT
    MOCK_FAILED_IMPORT = True


def _unmock_import():
    """Helper to reenable imports in tests."""
    global MOCK_ALL_IMPORT
    MOCK_ALL_IMPORT = False

    global MOCK_FAILED_IMPORT
    MOCK_FAILED_IMPORT = False


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
        self.failed_import = False
        self.record = warnings.catch_warnings(record=True)
        self._benchmark_dir = BENCHMARK_DIR

    def __enter__(self):
        # Mock import to speed up import
        if MOCK_ALL_IMPORT or MOCK_FAILED_IMPORT:
            sys.meta_path.insert(0, MockFinder())

        # Catch the import warning except if install errors are raised.
        if not RAISE_INSTALL_ERROR:
            self.record.__enter__()

        return self

    def __exit__(self, exc_type, exc_value, tb):
        if MOCK_ALL_IMPORT or MOCK_FAILED_IMPORT:
            sys.meta_path.pop(0)
            self.failed_import = True
            self.import_error = exc_type, exc_value, tb

        # Prevent import error from propagating and tag
        if exc_type is not None and issubclass(exc_type, ImportError):
            self.failed_import = True
            self.import_error = exc_type, exc_value, tb

        if not RAISE_INSTALL_ERROR:
            self.record.__exit__(exc_type, exc_value, tb)

        # Returning True in __exit__ prevent error propagation
        return self.failed_import
