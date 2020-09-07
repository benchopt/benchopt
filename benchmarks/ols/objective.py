from benchopt.base import BaseObjective


class Objective(BaseObjective):
    name = "Ordinary Least Squares"

    parameters = {
        'fit_intercept': [False],
    }

    def __init__(self, fit_intercept=False):
        self.fit_intercept = fit_intercept

    def set_data(self, X, y):
        self.X, self.y = X, y

    def __call__(self, beta):
        diff = self.y - self.X.dot(beta)
        return .5 * diff.dot(diff)

    def to_dict(self):
        return dict(X=self.X, y=self.y, fit_intercept=self.fit_intercept)
