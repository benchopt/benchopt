import numpy as np


from benchopt.base import BaseSolver


class Solver(BaseSolver):
    """Baseline is gradient descent, optionally accelerated."""
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
        w_acc = np.zeros(n_features)
        w_old = np.zeros(n_features)
        t_new = 1
        for _ in range(n_iter):
            if self.use_acceleration:
                t_old = t_new
                t_new = (1 + np.sqrt(1 + 4 * t_old ** 2)) / 2
                w_old[:] = w  # x in Beck & Teboulle (2009) notation
                w[:] = w_acc  # y in Beck & Teboulle (2009) notation
            w -= self.X.T.dot(self.X.dot(w) - self.y) / L
            if self.use_acceleration:
                w_acc[:] = w + (t_old - 1.) / t_new * (w - w_old)
        self.w = w

    def get_result(self):
        return self.w
