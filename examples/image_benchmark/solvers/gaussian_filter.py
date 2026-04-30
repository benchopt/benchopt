from benchopt import BaseSolver
import numpy as np


class Solver(BaseSolver):
    """Gaussian filtering (iterative smoothing) solver.

    Applies a box filter repeatedly, each pass smoothing the signal
    more. Stores every iterate so the ImagePlot can visualise the
    progression.
    """
    name = "gaussian_filter"

    requirements = ["scikit-image"]

    sampling_strategy = "callback"

    parameters = {"sigma": [0.5, 1.5]}

    def set_objective(self, X_noisy):
        self.X_noisy = X_noisy
        self.X_hat = X_noisy.copy()
        self.iterates = []

    def run(self, cb):
        from skimage.filters import gaussian
        self.X_hat = self.X_noisy.copy()
        self.iterates = [self.X_hat.copy()]
        while cb(self):
            self.X_hat = gaussian(self.X_hat, sigma=self.sigma)
            self.iterates.append(self.X_hat.copy())

    def get_result(self):
        return dict(X_hat=self.X_hat, iterates=self.iterates)
