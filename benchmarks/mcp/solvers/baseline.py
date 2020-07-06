import numpy as np


from benchopt.base import BaseSolver


class Solver(BaseSolver):
    name = 'Baseline'  # proximal gradient, optionally accelerated

    # any parameter defined here is accessible as a class attribute
    parameters = {
        'use_acceleration': [False],
    }

    def set_objective(self, X, y, lmbd, gamma):
        self.X, self.y, self.lmbd, self.gamma = X, y, lmbd, gamma

    def run(self, n_iter):
        L = np.linalg.norm(self.X, ord=2) ** 2
        n_features = self.X.shape[1]
        w = np.zeros(n_features)
        t_new = 1.
        for _ in range(n_iter):
            if self.use_acceleration:
                t_old = t_new
                t_new = (1 + np.sqrt(1 + 4 * t_old ** 2)) / 2
                w_old = w.copy()
            grad = self.X.T.dot(self.X.dot(w) - self.y)
            w -= grad / L
            w = self.prox_mcp(w, self.lmbd, self.gamma, L)
            if self.use_acceleration:
                w += (t_old - 1.) / t_new * (w - w_old)
        self.w = w

    def prox_mcp(self, w, lmbd, gamma, L):
        small_idx = np.abs(w) < gamma * self.lmbd
        w[small_idx] -= np.clip(w[small_idx], -lmbd / L, lmbd / L)
        w[small_idx] /= (1. - 1. / (gamma * L))
        return w

    def get_result(self):
        return self.w
