import sys
import warnings
from pathlib import Path

from ..config import RAISE_INSTALL_ERROR
from .dynamic_modules import _get_module_from_file

SKIP_IMPORT = False
BENCHMARK_DIR = None


class SkipWithBlock(Exception):
    pass


def skip_import():
    global SKIP_IMPORT
    SKIP_IMPORT = True


def set_benchmark(benchmark_dir):
    global BENCHMARK_DIR
    BENCHMARK_DIR = Path(benchmark_dir)


class safe_import_context:
    """Context used to manage import in benchmarks.

    This context allows to avoid errors on ImportError, to be able to report
    that a solver/dataset is not installed.

    Moreover, this context also allows to skip the import when simply listing
    all solvers, for benchmark's installation or auto completion. Note that all
    costly imports should be protected with this import for benchopt to perform
    best.

    This context is also used to import module dynamically from the ``utils``
    folder of a benchmark, using the
    :func:`~benchopt.safe_import_context.import_from` method.
    See :ref:`benchmark_utils_import` for a detailed explanation of this part.

    Finally, this context also catches import warnings.
    """

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

    def import_from(self, module_name, obj=None):
        """Dynamically import a module from BENCHMARK_DIR/utils.

        Parameters
        ----------
        module_name: str
            Name of the module to import. It can be a module with a simple
            ``*.py`` file, or a more complex package with a ``__init__.py``
            file. The naming convention for import is the same, with submodules
            separated with ``.``. The module is imported directly from the
            BENCHMARK_DIR/utils/ folder.
        obj: str or None
            If ``obj`` is provided, the module is imported and only the
            attribute named ``obj`` from this module is returned.

        Returns
        -------
        module or obj: object
            Module or object imported dynamically.
        """
        module_path = BENCHMARK_DIR / 'utils' / module_name.replace('.', '/')
        if not module_path.exists():
            module_path = module_path.with_suffix('.py')
        elif module_path.is_dir():
            module_path = module_path / '__init__.py'
        if not module_path.exists():
            raise ValueError(
                f"Failed to import {module_name}. Check that file "
                f" {module_path} exists in the benchmark."
            )
        module = _get_module_from_file(module_path, BENCHMARK_DIR)
        if obj is None:
            return module
        else:
            return getattr(module, obj)

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
