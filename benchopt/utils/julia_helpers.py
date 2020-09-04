import julia

from .stream_redirection import SuppressStd


# Factory to get the julia interpreter only once
jl_interpreter = None


def get_jl_interpreter():
    global jl_interpreter
    if jl_interpreter is None:
        out = SuppressStd()
        try:
            with out:
                # configure the julia runtime
                runtime_config = {'compiled_modules': False}
                julia.install()
                jl_interpreter = julia.Julia(**runtime_config)
        except BaseException:
            print(out.output)
            raise

    return jl_interpreter
