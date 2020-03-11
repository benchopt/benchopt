import numpy as np
from scipy import sparse
from numba import njit

from numpy.linalg import norm

from benchopt.base import BaseSolver


@njit
def st(x, mu):
    if x > mu:
        return x - mu
    if x < - mu:
        return x + mu
    return 0


class Solver(BaseSolver):
    name = "cd"

    install_cmd = None

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd
        # self.run(1)

    def run(self, n_iter):
        if sparse.issparse(self.X):
            L = sparse.linalg.norm(self.X, axis=0) ** 2
            self.w = self.sparse_cd(
                self.X.data, self.X.indices, self.X.indptr, self.y, self.lmbd,
                L, n_iter)
        else:
            L = norm(self.X, axis=0) ** 2
            self.w = self.cd(self.X, self.y, self.lmbd, L, n_iter)

    @staticmethod
    @njit
    def cd(X, y, lmbd, L, n_iter):
        n_features = X.shape[1]
        R = np.copy(y)
        w = np.zeros(n_features)
        for _ in range(n_iter):
            for j in range(n_features):
                old = w[j]
                w[j] = st(w[j] + X[:, j] @ R / L[j], lmbd / L[j])
                diff = old - w[j]
                if diff != 0:
                    R += diff * X[:, j]
        return w

    @staticmethod
    @njit
    def sparse_cd(X_data, X_indices, X_indptr, y, lmbd, L, n_iter):
        n_features = len(X_indptr) - 1
        w = np.zeros(n_features)
        R = np.copy(y)
        for _ in range(n_iter):
            for j in range(n_features):
                old = w[j]
                start, end = X_indptr[j:j+2]
                scal = 0.
                for ind in range(start, end):
                    scal += X_data[ind] * R[X_indices[ind]]
                w[j] = st(w[j] + scal / L[j], lmbd / L[j])
                diff = old - w[j]
                if diff != 0:
                    for ind in range(start, end):
                        R[X_indices[ind]] += diff * X_data[ind]
        return w

    def get_result(self):
        return self.w
