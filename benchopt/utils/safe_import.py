import warnings
import sys

from ..config import RAISE_INSTALL_ERROR

SKIP_IMPORT = False


class SkipWithBlock(Exception):
    pass


def skip_import():
    global SKIP_IMPORT
    SKIP_IMPORT = True


class safe_import_context:
    """Do not fail on ImportError and catch import warnings"""

    def __init__(self):
        self.failed_import = False
        self.record = warnings.catch_warnings(record=True)

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
