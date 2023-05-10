from benchopt import BaseSolver
from benchopt import safe_import_context

with safe_import_context() as import_ctx:
    import numpy as np
    import dummy_solver_import
    from benchmark_utils import dummy_function
    from benchmark_utils.dummy_submodule.dummy_subsubmodule import (
        error_raiser
    )


class Solver(BaseSolver):
    name = 'Solver-Test'

    parameters = {'raise_error': [False]}

    def __init__(self, raise_error=False):
        self.raise_error = raise_error

    def skip(self, X, y, lmbd):
        if lmbd == 0:
            return True, "lmbd=0"
        return False, None

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd

    def run(self, n_iter):
        # make sure that the imported modules are working
        dummy_solver_import.__version__
        dummy_function()

        if self.raise_error:
            error_raiser()

        L = np.linalg.norm(self.X) ** 2

        n_features = self.X.shape[1]
        w = np.zeros(n_features)

        for _ in range(n_iter):
            w -= self.X.T @ (self.X @ w - self.y) / L
            w = self.st(w, self.lmbd / L)

        self.w = w

    def st(self, w, mu):
        w -= np.clip(w, -mu, mu)
        return w

    def get_result(self):
        return self.w

    @staticmethod
    def get_next(stop_val):
        return stop_val + 1
