import sys
import warnings
import importlib

from importlib.abc import Loader, MetaPathFinder
from pathlib import Path
from unittest.mock import Mock

from joblib.externals import cloudpickle

from ..config import RAISE_INSTALL_ERROR


MOCK_IMPORT = False
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
    def find_spec(self, fullname, path, target=None):
        return importlib.util.spec_from_loader(fullname, MockLoader(fullname))


def mock_import():
    global MOCK_IMPORT
    MOCK_IMPORT = True


def _unmock_import():
    """Helper to reenable imports in tests."""
    global MOCK_IMPORT
    MOCK_IMPORT = False


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
        if MOCK_IMPORT:
            sys.meta_path.insert(0, MockFinder())

        # Catch the import warning except if install errors are raised.
        if not RAISE_INSTALL_ERROR:
            self.record.__enter__()

        return self

    def __exit__(self, exc_type, exc_value, tb):
        if MOCK_IMPORT:
            sys.meta_path.pop(0)

            self.failed_import = True

        # Prevent import error from propagating and tag
        if exc_type is not None and issubclass(exc_type, ImportError):
            self.failed_import = True
            self.import_error = exc_type, exc_value, tb

        if not RAISE_INSTALL_ERROR:
            self.record.__exit__(exc_type, exc_value, tb)

        # Returning True in __exit__ prevent error propagation
        return self.failed_import
