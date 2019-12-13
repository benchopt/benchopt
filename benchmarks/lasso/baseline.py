import numpy as np


from benchopt.base import Solver


class Baseline(Solver):
    name = 'Baseline'

    def set_loss(self, X, y, lmbd):
        self.X = X
        self.y = y
        self.lmbd = lmbd

        self.L = np.linalg.norm(X.dot(X.T), ord=2)

    def run(self, n_iter):
        n_features = self.X.shape[1]
        z_hat = np.zeros(n_features)
        for i in range(n_iter):
            grad = self.X.T.dot(self.X.dot(z_hat) - self.y)
            z_hat -= 1 / self.L * grad
            z_hat = self.st(z_hat, 1 / self.L * self.lmbd)
        self.z_hat = z_hat

    def st(self, z, mu):
        return np.sign(z) * np.maximum(0, abs(z) - mu)

    def get_result(self):
        return self.z_hat
