"A context manager to handle exception with option to open a debugger."
from contextlib import contextmanager


# Get config values
from ..config import DEBUG


class StatusHandler(object):
    def __init__(self):
        self.status = 'running'


@contextmanager
def exception_handler(output, pdb=False):
    """Context manager to handle exception with option to open a debugger.

    Parameter
    ---------
    output : TerminalOutput
        Object to format string to display the progress of the solver.
    pdb : bool
        If set to True, open a debugger if an error is raised.
    """
    ctx = StatusHandler()
    try:
        yield ctx
    except KeyboardInterrupt:
        ctx.status = 'interrupted'
        raise SystemExit(1)
    except BaseException:
        ctx.status = 'interrupted'

        if pdb:
            # Use ipdb if it is available and default to pdb otherwise.
            try:
                from ipdb import post_mortem
            except ImportError:
                from pdb import post_mortem
            post_mortem()

        if DEBUG:
            raise
        else:
            import traceback
            traceback.print_exc()
