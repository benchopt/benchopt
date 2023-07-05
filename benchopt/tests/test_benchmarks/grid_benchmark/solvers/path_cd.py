from benchopt import safe_import_context
from benchopt.helpers.grid_solver import BaseGridSolver

with safe_import_context() as import_ctx:
    import numpy as np

def st(x, mu):
    return np.sign(x) * np.maximum(np.abs(x) - mu)


class Solver(BaseGridSolver):
    name = "path_cd"
    parameter = {"cd_iter": [1_000]}

    def set_objective(self, X, y, lmbd_grid):
        self.X = X
        self.y = y
        self.L = (self.X ** 2).sum(axis=0)
        self.grid_values = lmbd_grid

    def run_grid_value(self, lmbd, w):
        w = np.copy(w)
        n = self.X.shape[1]
        r = np.copy(self.y)
        for _ in range(self.cd_iter):
            for j in range(n):
                if self.L[j] == 0.:
                    continue
                old = w[j]
                w[j] = st(w[j] + (self.X[:, j] @ r) / self.L[j], lmbd / self.L[j])
                d = old - w[j]
                if d != 0:
                    r += d * self.X[:, j]
        return w

