from benchopt.base import BaseObjective


class Objective(BaseObjective):
    name = "Dummy Sparse Regression"

    parameters = {
        'reg': [0.05, .1, .5]
    }

    def __init__(self, reg=.1, fit_intercept=False):
        self.reg = reg
        self.fit_intercept = fit_intercept

    def set_data(self, X, y):
        self.X, self.y = X, y
        self.lmbd = self.reg * self._get_lambda_max()

    def compute(self, beta):
        diff = self.y - self.X.dot(beta)
        objective_value = .5 * diff.dot(diff) + self.lmbd * abs(beta).sum()

        # To test for multiple type of return value, makes this depend on the
        # parameter:
        #   - reg == .1: Return a scalar
        #   - reg < .1: Return a scalar value for `objective_value`
        #   - reg > .1: Return multiple objective values
        if self.reg == .1:
            return objective_value
        elif self.reg < .1:
            return dict(objective_value=objective_value)
        else:
            return dict(objective_value=objective_value, val=objective_value)

    def _get_lambda_max(self):
        return abs(self.X.T.dot(self.y)).max()

    def to_dict(self):
        return dict(X=self.X, y=self.y, lmbd=self.lmbd)
