import numpy as np


from benchopt.base import BaseObjective


class Objective(BaseObjective):
    name = "L2 Logistic Regression"

    parameters = {
        'fit_intercept': [False],
        'lmbd': [1., 0.01]
    }

    def __init__(self, lmbd=.1, fit_intercept=False):
        self.lmbd = lmbd
        self.fit_intercept = fit_intercept

    def set_data(self, X, y):
        self.X, self.y = X, y

    def compute(self, beta):
        y_X_beta = self.y * self.X.dot(beta.flatten())
        l2 = 0.5 * np.dot(beta, beta)
        return np.log1p(np.exp(-y_X_beta)).sum() + self.lmbd * l2

    def to_dict(self):
        return dict(X=self.X, y=self.y, lmbd=self.lmbd)
