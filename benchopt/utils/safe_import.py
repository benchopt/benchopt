import sys
import warnings

from ..config import RAISE_INSTALL_ERROR

SKIP_IMPORT = False
BENCHMARK_DIR = None


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

    def __enter__(self):
        warnings.warn(
            "safe_import_context is deprecated in benchopt 1.7. You can now "
            "directly import all modules as in a regular Python script.",
            DeprecationWarning
        )
        return self

    def __exit__(self, exc_type, exc_value, tb):
        return False
