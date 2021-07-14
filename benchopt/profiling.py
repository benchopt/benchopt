from .globals import globals

if globals["DO_PROFILE"]:
    import line_profiler
    profile = line_profiler.LineProfiler()
else:
    class Profile:
        def __call__(self, func):
            return func

        def print_stats(self):
            return

    profile = Profile()
