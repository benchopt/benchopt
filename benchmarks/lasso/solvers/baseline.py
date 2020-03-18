import numpy as np


from benchopt.base import BaseSolver


class Solver(BaseSolver):
    name = 'Baseline'

    parameters = {'use_acceleration': [False, True]}

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd

        self.L = np.linalg.norm(self.X.dot(self.X.T), ord=2)

    def run(self, n_iter):
        n_features = self.X.shape[1]
        z_hat = np.zeros(n_features)
        t_new = 1
        for _ in range(n_iter):
            if self.use_acceleration:
                t_old = t_new
                t_new = (1 + np.sqrt(1 + 4 * t_old ** 2)) / 2
                z_old = z_hat.copy()
            grad = self.X.T.dot(self.X.dot(z_hat) - self.y)
            z_hat -= 1 / self.L * grad
            z_hat = self.st(z_hat, 1 / self.L * self.lmbd)
            if self.use_acceleration:
                z_hat = z_hat + (t_old - 1.) / t_new * (z_hat - z_old)
        self.z_hat = z_hat

    def st(self, z, mu):
        return np.sign(z) * np.maximum(0, np.abs(z) - mu)

    def get_result(self):
        return self.z_hat
