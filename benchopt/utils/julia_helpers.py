import julia
from contextlib import contextmanager

from ..config import DEBUG
from .stream_redirection import SuppressStd


# nullcontext is not available in python <=3.6 so we resort to this
# for backward compat.
@contextmanager
def nullcontext(enter_result=None):
    yield enter_result


# Singleton to get the julia interpreter only once
jl_interpreter = None


def get_jl_interpreter():
    global jl_interpreter
    if jl_interpreter is None:
        # Only suppress std if not in debug mode.
        out = nullcontext() if DEBUG else SuppressStd()
        try:
            with out:
                # configure the julia runtime
                runtime_config = {
                    'compiled_modules': False,
                    'debug': bool(DEBUG)
                }
                julia.install()
                jl_interpreter = julia.Julia(**runtime_config)
        except BaseException:
            if hasattr(out, 'output'):
                print(out.output)
            raise

    return jl_interpreter
