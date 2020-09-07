import numpy as np


from benchopt.base import BaseSolver


class Solver(BaseSolver):
    name = 'Python-PGD'  # proximal gradient, optionally accelerated

    # any parameter defined here is accessible as a class attribute
    parameters = {'use_acceleration': [False, True]}

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd

    def run(self, n_iter):
        L = np.linalg.norm(self.X, ord=2) ** 2

        n_features = self.X.shape[1]
        w = np.zeros(n_features)
        t_new = 1
        for _ in range(n_iter):
            if self.use_acceleration:
                t_old = t_new
                t_new = (1 + np.sqrt(1 + 4 * t_old ** 2)) / 2
                w_old = w.copy()
            grad = self.X.T.dot(self.X.dot(w) - self.y)
            w -= grad / L
            w = self.st(w, self.lmbd / L)
            if self.use_acceleration:
                w += (t_old - 1.) / t_new * (w - w_old)
        self.w = w

    def st(self, w, mu):
        w -= np.clip(w, -mu, mu)
        return w

    def get_result(self):
        return self.w
