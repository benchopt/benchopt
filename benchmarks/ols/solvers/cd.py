import numpy as np

from benchopt.base import BaseSolver
from benchopt.util import safe_import
from warnings import filterwarnings


with safe_import() as solver_import:
    from scipy import sparse
    from numba import njit
    from numba.errors import PerformanceWarning


if solver_import.failed_import:

    def njit(f):  # noqa: F811
        return f


class Solver(BaseSolver):
    name = "cd"

    install_cmd = 'pip'
    requirements = ['numba', 'scipy']

    def set_objective(self, X, y, fit_intercept=False):
        self.X, self.y = X, y
        self.fit_intercept = fit_intercept

        # Make sure we cache the numba compilation.
        self.run(1)

    def run(self, n_iter):
        filterwarnings("ignore", category=PerformanceWarning)
        L = (self.X ** 2).sum(axis=0)
        if sparse.issparse(self.X):
            self.w = self.sparse_cd(
                self.X.data, self.X.indices, self.X.indptr, self.y,
                L, n_iter)
        else:
            self.w = self.cd(self.X, self.y, L, n_iter)

    @staticmethod
    @njit
    def cd(X, y, L, n_iter):
        n_features = X.shape[1]
        R = np.copy(y)
        w = np.zeros(n_features)
        for _ in range(n_iter):
            for j in range(n_features):
                if L[j] == 0.:
                    continue
                old = w[j]
                w[j] = w[j] + X[:, j] @ R / L[j]
                diff = old - w[j]
                if diff != 0:
                    R += diff * X[:, j]
        return w

    @staticmethod
    @njit
    def sparse_cd(X_data, X_indices, X_indptr, y, L, n_iter):
        n_features = len(X_indptr) - 1
        w = np.zeros(n_features)
        R = np.copy(y)
        for _ in range(n_iter):
            for j in range(n_features):
                if L[j] == 0.:
                    continue
                old = w[j]
                start, end = X_indptr[j:j+2]
                scal = 0.
                for ind in range(start, end):
                    scal += X_data[ind] * R[X_indices[ind]]
                w[j] = w[j] + scal / L[j]
                diff = old - w[j]
                if diff != 0:
                    for ind in range(start, end):
                        R[X_indices[ind]] += diff * X_data[ind]
        return w

    def get_result(self):
        return self.w
