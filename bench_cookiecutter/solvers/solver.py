from benchopt import BaseSolver
from benchopt import safe_import_context

with safe_import_context() as import_ctx:
    # your dependencies here
    pass


class Solver(BaseSolver):
    name = "{name}"

    def __init__(self):
        pass

    def set_objective(self):
        pass

    def run(self, stop_value):
        pass

    def get_result(self):
        return
