from benchopt import BaseSolver
from benchopt import safe_import_context

with safe_import_context() as import_ctx:
    import numpy as np


class Solver(BaseSolver):
    name = 'Test-Solver'

    def skip(self, X, y, lmbd):
        if lmbd == 0:
            return True, "lmbd=0"
        return False, None

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd

    def run(self, n_iter):

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
