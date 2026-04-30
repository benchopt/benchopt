from benchopt import BaseObjective
import numpy as np


class Objective(BaseObjective):
    """2D signal denoising benchmark.

    Each solver tries to denoise a noisy 2D signal (image).
    The objective measures the reconstruction error.
    Solvers store their intermediate iterates so that the
    custom ImagePlot can display convergence visually.
    """
    name = "Image Denoising"

    def set_data(self, X_true, X_noisy):
        self.X_true = X_true
        self.X_noisy = X_noisy

    def get_objective(self):
        return dict(X_noisy=self.X_noisy)

    def evaluate_result(self, X_hat, iterates=None):
        value = np.mean((self.X_true - X_hat) ** 2)
        result = dict(value=value)
        # Store iterates in the result so the ImagePlot can access them.
        if iterates is not None:
            result["iterates"] = iterates
        return result

    def get_one_result(self):
        return dict(X_hat=self.X_noisy, iterates=None)
