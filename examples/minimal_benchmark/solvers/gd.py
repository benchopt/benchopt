from benchopt import BaseSolver
import numpy as np


class Solver(BaseSolver):
    name = 'gd'
    sampling_strategy = 'callback'

    parameters = {'lr': [1e-3]}

    def set_objective(self, X):
        self.X = X
        self.X_hat = np.zeros_like(X)

    def run(self, cb):
        while cb():
            self.X_hat = self.X_hat - self.lr * (self.X_hat - self.X)

    def get_result(self):
        return {'X_hat': self.X_hat}
