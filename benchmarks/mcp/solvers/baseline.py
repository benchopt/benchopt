import numpy as np


from benchopt.base import BaseSolver


def st(x, mu):
    if x > mu:
        return x - mu
    if x < - mu:
        return x + mu
    return 0


def prox_mcp(x, lmbd, gamma):
    if x > gamma * lmbd:
        return x
    if x < - gamma * lmbd:
        return x
    return gamma / (gamma - 1) * st(x, lmbd)


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
            w = self.prox_mcp_vec(w,
                                  self.lmbd * (n_samples * norms2)**0.5 / L,
                                  self.gamma * L / norms2)
            if self.use_acceleration:
                w += (t_old - 1.) / t_new * (w - w_old)
        self.w = w

    def prox_mcp_vec(self, w, lmbd, gamma):
        for j in range(len(w)):
            w[j] = prox_mcp(w[j], lmbd[j], gamma[j])
        return w

    def get_result(self):
        return self.w