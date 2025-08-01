import numpy as np

from benchopt import BaseSolver


class Solver(BaseSolver):
    name = 'test-solver'

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd

    def run(self, n_iter): pass

    def get_result(self):
        return {'beta': np.ones(self.X.shape[1])}
