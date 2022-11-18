from benchopt import BaseSolver
from benchopt import safe_import_context

# Test that we get a comprehensve error when a submodule of benchmark_utils
# raises an ValueError
with safe_import_context() as import_ctx:
    from benchmark_utils import import_error  # noqa: F401


class Solver(BaseSolver):
    name = 'ImportError'
    parameters = {}

    def set_objective(self, **objective_dict): pass
    def run(self, n_iter): pass
    def get_result(self): pass
