from benchopt import BaseSolver, safe_import_context

with safe_import_context() as import_ctx:
    import numpy as np


class Solver(BaseSolver):
    name = 'Dummy solver'
    stopping_strategy = "callback"

    def set_objective(self, X):
        self.X = X

    def run(self, callback):

        n_features = self.X.shape[1]
        w = np.ones(n_features)

        while callback(w):
            w *= 0.9

        self.w = w

    def get_result(self):
        return self.w
