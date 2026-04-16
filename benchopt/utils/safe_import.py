import sys
import warnings

from ..config import RAISE_INSTALL_ERROR
from . import dynamic_modules


class SkipWithBlock(Exception):
    pass


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

    def __enter__(self):
        # Skip context if necessary to speed up import
        if dynamic_modules.SKIP_IMPORT:
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

        if dynamic_modules.SKIP_IMPORT:
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
