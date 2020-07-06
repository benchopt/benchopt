import numpy as np

from benchopt.base import BaseSolver
from benchopt.util import safe_import

with safe_import() as solver_import:
    from scipy import sparse
    from numba import njit

if solver_import.failed_import:

    def njit(f):  # noqa: F811
        return f


@njit
def st(x, mu):
    if x > mu:
        return x - mu
    if x < - mu:
        return x + mu
    return 0

@njit
def prox_mcp(x, lmbd, gamma, Lj):
    # prox associated to 1/L * pen_MCP
    if x > gamma * lmbd:
        return x
    if x < - gamma * lmbd:
        return x
    return 1. / (1. - 1. / (Lj * gamma)) * st(x, lmbd / Lj)
    # return st(x, lmbd/L)

class Solver(BaseSolver):
    name = "cd"

    install_cmd = 'pip'
    requirements = ['numba', 'scipy']

    def set_objective(self, X, y, lmbd, gamma):
        self.X, self.y, self.lmbd, self.gamma = np.asfortranarray(X), y, lmbd, gamma
        # Make sure we cache the numba compilation.
        self.run(1)

    def run(self, n_iter):
        L = (self.X ** 2).sum(axis=0)
        if sparse.issparse(self.X):
            self.w = self.sparse_cd(
                self.X.data, self.X.indices, self.X.indptr, self.y, self.lmbd,
                self.gamma, L, n_iter)
        else:
            self.w = self.cd(self.X, self.y, self.lmbd, self.gamma, L, n_iter)

    @staticmethod
    @njit
    def cd(X, y, lmbd, gamma, L, n_iter):
        n_features = X.shape[1]
        R = np.copy(y)
        w = np.zeros(n_features)
        for _ in range(n_iter):
            for j in range(n_features):
                if L[j] == 0.:
                    continue
                old = w[j]
                w[j] = prox_mcp(w[j] + X[:, j] @ R / L[j], lmbd, gamma, L[j])
                diff = old - w[j]
                if diff != 0:
                    R += diff * X[:, j]
            print(w)
        return w

    @staticmethod
    @njit
    def sparse_cd(X_data, X_indices, X_indptr, y, lmbd, gamma, L, n_iter):
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
                w[j] = prox_mcp(w[j] + scal / L[j], lmbd, gamma, L[j])
                diff = old - w[j]
                if diff != 0:
                    for ind in range(start, end):
                        R[X_indices[ind]] += diff * X_data[ind]
        return w

    def get_result(self):
        return self.w
