from benchopt.base import BaseObjective


class Objective(BaseObjective):
    name = "Lasso Regression"

    parameters = { # regularization parameters in a dict
        'reg': [0.05, .1, .5]
    }

    def __init__(self, reg=.1):
        self.reg = reg

    def set_data(self, X, y):
        self.X, self.y = X, y
        self.lmbd = self.reg * self._get_lambda_max()

    def compute(self, beta):
        """Objective value at one iteration"""
        diff = self.y - self.X.dot(beta)
        return .5 * diff.dot(diff) + self.lmbd * abs(beta).sum()

    def _get_lambda_max(self):
        return abs(self.X.T.dot(self.y)).max()

    def to_dict(self):
        """Objects needed for a solver to run the set_objective method"""
        return dict(X=self.X, y=self.y, lmbd=self.lmbd)
