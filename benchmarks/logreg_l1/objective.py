import numpy as np


from benchopt.base import BaseObjective


class Objective(BaseObjective):
    name = "Sparse Logistic Regression"

    parameters = {
        'fit_intercept': [False],
        'reg': [0.05, .1, .5]
    }

    def __init__(self, reg=.1, fit_intercept=False):
        self.reg = reg
        self.fit_intercept = fit_intercept

    def set_data(self, X, y):
        self.X, self.y = X, y
        self.lmbd = self.reg * self._get_lambda_max()

    def __call__(self, beta):
        y_X_beta = self.y * self.X.dot(beta.flatten())
        l1 = abs(beta).sum()
        return np.log(1 + np.exp(-y_X_beta)).sum() + self.lmbd * l1

    def _get_lambda_max(self):
        return abs(self.X.T.dot(self.y)).max()

    def to_dict(self):
        return dict(X=self.X, y=self.y, lmbd=self.lmbd)
        #           fit_intercept=self.fit_intercept)
