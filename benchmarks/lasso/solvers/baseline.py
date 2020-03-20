import numpy as np


from benchopt.base import BaseSolver


class Solver(BaseSolver):
    name = 'Baseline'  # proximal gradient, eventually accelerated

    # any parameter defined here is accessible as a class attribute
    parameters = {'use_acceleration': [False, True]}

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd

        self.L = np.linalg.norm(self.X, ord=2) ** 2

    def run(self, n_iter):
        n_features = self.X.shape[1]
        w = np.zeros(n_features)
        t_new = 1
        for _ in range(n_iter):
            if self.use_acceleration:
                t_old = t_new
                t_new = (1 + np.sqrt(1 + 4 * t_old ** 2)) / 2
                w_old = w.copy()
            grad = self.X.T.dot(self.X.dot(w) - self.y)
            w -= 1 / self.L * grad
            w = self.st(w, 1 / self.L * self.lmbd)
            if self.use_acceleration:
                w = w + (t_old - 1.) / t_new * (w - w_old)
        self.w = w

    def st(self, w, mu):
        return np.sign(w) * np.maximum(0, np.abs(w) - mu)

    def get_result(self):
        return self.w
