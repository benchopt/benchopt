"A context manager to handle exception with option to open a debugger."
import traceback
from contextlib import contextmanager


# Get config values
from ..config import DEBUG


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
        ctx.status = 'interrupted'
        terminal.stop(None, 'interrupted')
        if hasattr(terminal, 'live'):
            terminal.live.update(terminal.render_tree())
        raise SystemExit(1)
    except BaseException:
        ctx.status = 'error'

        if pdb:
            traceback.print_exc()
            # Use ipdb if it is available and default to pdb otherwise.
            try:
                from ipdb import post_mortem
            except ImportError:
                from pdb import post_mortem
            post_mortem()

        if DEBUG:
            raise
        else:
            print()
            traceback.print_exc()
