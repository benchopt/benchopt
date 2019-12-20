import numpy as np
from blitzl1 import LassoProblem

from benchopt.base import BaseSolver


class Solver(BaseSolver):
    name = 'Blitz'

    def set_loss(self, X, y, lmbd):
        self.X = X.astype(np.float32)
        self.y = y.astype(np.float32)
        self.lmbd = lmbd

        self.problem = LassoProblem(self.X, self.y)

    def run(self, n_iter):
        self.coef_ = self.problem.solve(self.lmbd)

    def get_result(self):
        return self.coef_.flatten()
