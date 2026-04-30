from benchopt import BaseSolver
import numpy as np


class Solver(BaseSolver):
    """Total-variation proximal gradient descent solver.

    Minimises  0.5*||X - X_noisy||^2 + lam * TV(X)  via projected
    gradient descent on the dual. Stores every iterate so the
    ImagePlot can visualise the progression.
    """
    name = "tv_denoise"

    requirements = ["scikit-image"]

    sampling_strategy = "callback"

    parameters = {"lam": [0.1, 0.3]}

    def set_objective(self, X_noisy):
        self.X_noisy = X_noisy
        self.X_hat = X_noisy.copy()
        self.iterates = []

    def run(self, cb):
        from skimage.restoration import denoise_tv_chambolle
        self.X_hat = self.X_noisy.copy()
        self.iterates = [self.X_hat.copy()]
        while cb(self):
            self.X_hat = denoise_tv_chambolle(
                self.X_hat, weight=self.lam
            )
            self.iterates.append(self.X_hat.copy())

    def get_result(self):
        return dict(X_hat=self.X_hat, iterates=self.iterates)
