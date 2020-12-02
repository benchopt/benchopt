"A context manager to handle exception with option to open a debugger."
from contextlib import contextmanager

from .colorify import colorify, RED
from ..config import get_global_setting

# Use ipdb if it is available and default to pdb otherwise.
try:
    from ipdb import post_mortem
except ImportError:
    from pdb import post_mortem


# Get config values
DEBUG = get_global_setting('debug')


@contextmanager
def exception_handler(tag=None, pdb=False):
    """Context manager to handle exception with option to open a debugger.

    Parameter
    ---------
    tag: str
        Name to display before outputing error in red.
    pdb: bool
        If set to True, open a debugger if an error is raised.
    """
    try:
        yield
    except BaseException:
        status = colorify("error", RED)
        print(f"{tag} {status}".ljust(80))

        if pdb:
            post_mortem()

        if DEBUG:
            raise
        else:
            import traceback
            traceback.print_exc()
