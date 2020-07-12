import numpy as np


from benchopt.base import BaseSolver


def st(w, mu):
    # w -= np.clip(w, -mu, mu)
    # return w
    return np.sign(w) * np.maximum(np.abs(w) - mu, 0)


def prox_mcp(w, lmbd, gamma):
    mask = np.abs(w) < gamma * lmbd
    w[mask] = gamma[mask] / (gamma[mask] - 1) * st(w[mask], lmbd[mask])
    return w


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
        n_samples, n_features = self.X.shape
        norms2 = (self.X ** 2).sum(axis=0)
        w = np.zeros(n_features)
        t_new = 1.
        for _ in range(n_iter):
            if self.use_acceleration:
                t_old = t_new
                t_new = (1 + np.sqrt(1 + 4 * t_old ** 2)) / 2
                w_old = w.copy()
            grad = self.X.T.dot(self.X.dot(w) - self.y)
            w -= grad / L
            w = prox_mcp(w, self.lmbd * (n_samples * norms2)**0.5 / L,
                         self.gamma * L / norms2)
            if self.use_acceleration:
                w += (t_old - 1.) / t_new * (w - w_old)
        self.w = w

    def get_result(self):
        return self.w