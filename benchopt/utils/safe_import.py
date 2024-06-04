import sys
import warnings
import importlib
from pathlib import Path

from joblib.externals import cloudpickle

from ..config import RAISE_INSTALL_ERROR

SKIP_IMPORT = False
BENCHMARK_DIR = None
PACKAGE_NAME = "benchmark_utils"


class SkipWithBlock(Exception):
    pass


def skip_import():
    """Once called, all the safe_import_context is skipped."""
    global SKIP_IMPORT
    SKIP_IMPORT = True


def _unskip_import():
    """Helper to reenable imports in tests."""
    global SKIP_IMPORT
    SKIP_IMPORT = False


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

    Moreover, this context also allows to skip the import when simply listing
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
        # Skip context if necessary to speed up import
        if SKIP_IMPORT:
            # See https://stackoverflow.com/questions/12594148/skipping-execution-of-with-block  # noqa
            sys.settrace(lambda *args, **keys: None)
            frame = sys._getframe(1)
            frame.f_trace = self.trace
            return self

        # Catch the import warning except if install errors are raised.
        if not RAISE_INSTALL_ERROR:
            self.record.__enter__()
        return self

    def trace(self, frame, event, arg):
        raise SkipWithBlock()

    def __exit__(self, exc_type, exc_value, tb):

        if SKIP_IMPORT:
            self.failed_import = True
            self.import_error = (
                RuntimeError, "Should not check install with skip import", None
            )
            return True

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
