
USE_PROFILE = False
PROFILER = None


def use_profile():
    global USE_PROFILE
    USE_PROFILE = True


def get_profiler():
    global PROFILER
    if PROFILER is None:
        try:
            from line_profiler import LineProfiler
        except ImportError:
            raise ImportError("Need line-profiler installed to use "
                              "`--profile` option.")
        PROFILER = LineProfiler()
    return PROFILER


def profile(func):
    """Decorator to tell line profiler which function to profile.

    Typically, this can be used for the ``run`` method of a ``Solver``.
    Once the method is decorated, you can use ``--profile`` in
    ``benchopt run`` to get a profiling report.
    """
    global USE_PROFILE
    if not USE_PROFILE:
        return func
    return get_profiler()(func)


def print_stats():
    global PROFILER
    if PROFILER is not None:
        PROFILER.print_stats()
