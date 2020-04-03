import numpy as np


from benchopt.base import BaseSolver


class Solver(BaseSolver):
    """Baseline is proximal gradient, optionnaly accelerated."""
    name = 'Baseline'

    # any parameter defined here is accessible as a class attribute
    parameters = {'use_acceleration': [False, True]}

    def set_objective(self, X, y, fit_intercept=False):
        self.X, self.y = X, y
        self.fit_intercept = fit_intercept

    def run(self, n_iter):
        L = np.linalg.norm(self.X, ord=2) ** 2

        n_features = self.X.shape[1]
        w = np.zeros(n_features)
        t_new = 1
        z = w.copy()
        for i in range(n_iter):
            grad = self.X.T.dot(self.X.dot(z) - self.y)
            z -= grad / L
            w = np.maximum(z, 0)
            w_old = w.copy()
            if i >= (n_iter - 1):
                self.w = w
            if self.use_acceleration:
                t_old = t_new
                t_new = (1 + np.sqrt(1 + 4 * t_old ** 2)) / 2
                z += (t_old - 1.) / t_new * (w - w_old)

    def get_result(self):
        return self.w
