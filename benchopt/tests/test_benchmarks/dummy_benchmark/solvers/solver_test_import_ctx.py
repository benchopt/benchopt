from benchopt import BaseSolver
from benchopt import safe_import_context

with safe_import_context() as import_ctx_wrong_name:
    import numpy as np


class Solver(BaseSolver):
    name = "test_import_ctx"

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd

    def run(self, n_iter):
        pass

    def get_result(self):
        return np.zeros(self.X.shape[1])
