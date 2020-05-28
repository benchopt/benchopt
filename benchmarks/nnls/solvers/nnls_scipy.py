import numpy as np


from benchopt.base import BaseSolver
from benchopt.util import safe_import

with safe_import() as solver_import:
    from scipy.optimize._nnls import nnls


class Solver(BaseSolver):
    name = 'scipy'

    install_cmd = 'pip'
    requirements = ['scipy']

    def set_objective(self, X, y, fit_intercept=False):
        self.X, self.y = X, y
        self.fit_intercept = fit_intercept

    def run(self, n_iter):
        m, n = self.X.shape

        w = np.zeros((n,))
        zz = np.zeros((m,))
        index = np.zeros((n,), dtype=int)

        self.w, _, _ = \
            nnls(self.X, m, n, self.y, w, zz, index, n_iter)

    def get_result(self):
        return self.w
