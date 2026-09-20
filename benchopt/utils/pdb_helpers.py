"A context manager to handle exception with option to open a debugger."
import traceback
from contextlib import contextmanager


# Get config values
from ..config import DEBUG
from ..config import RAISE_ON_ERROR


class StatusHandler(object):
    def __init__(self):
        self.status = 'running'


@contextmanager
def exception_handler(terminal, pdb=False):
    """Context manager to handle exception with option to open a debugger.

    Parameter
    ---------
    terminal : TerminalOutput
        Object to format string to display the progress of the solver.
    pdb : bool
        If set to True, open a debugger if an error is raised.
    """
    ctx = StatusHandler()
    try:
        yield ctx
    except KeyboardInterrupt:
        print(end='', flush=True)
        ctx.status = 'interrupted'
        raise
    except BaseException:
        print(end='', flush=True)
        ctx.status = 'error'

        if pdb:
            terminal.show_status('error')
            traceback.print_exc()
            # Use ipdb if it is available and default to pdb otherwise.
            try:
                from ipdb import post_mortem
            except ImportError:
                from pdb import post_mortem
            post_mortem()

        # Re-raise on the first error to make the run fail fast. `DEBUG` keeps
        # this behavior for backward compatibility, but `raise_on_error` offers
        # it without turning on any of the extra debug logging.
        if DEBUG or RAISE_ON_ERROR:
            terminal.show_status('error')
            raise
        else:
            print()
            traceback.print_exc()
