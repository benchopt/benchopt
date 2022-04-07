from benchopt import BaseObjective, safe_import_context


with safe_import_context() as import_ctx:
    import numpy as np

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

    def skip(self):
        if np.testing.assert_array_equal(self.X, np.zeros((2, 2))):
            return True, 'X is all zeros'
        return False, None

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
            return dict(value=objective_value)
        else:
            return dict(value=objective_value, val=objective_value * 4)

    def _get_lambda_max(self):
        return abs(self.X.T.dot(self.y)).max()

    def to_dict(self):
        return dict(X=self.X, y=self.y, lmbd=self.lmbd)
