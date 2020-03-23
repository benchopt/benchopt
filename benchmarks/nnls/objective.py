from benchopt.base import BaseObjective
import numpy as np


class Objective(BaseObjective):
    name = "Non Negative Least Squares"

    parameters = {
        'fit_intercept': [False],
    }

    def __init__(self, fit_intercept=False):
        self.fit_intercept = fit_intercept

        super().__init__()

    def set_data(self, X, y):
        self.X, self.y = X, y

    def __call__(self, beta):
        if (beta < 0).any():
            diff = self.y - self.X.dot(beta)
            return .5 * diff.dot(diff)
        else:
            return np.inf
        # diff = self.y - self.X.dot(beta)
        # return .5 * diff.dot(diff)

    def to_dict(self):
        return dict(X=self.X, y=self.y)
