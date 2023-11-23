from benchopt import BaseObjective, safe_import_context


with safe_import_context() as import_ctx:
    import numpy as np


class Objective(BaseObjective):
    """Here one can provide a description of the Objective.

    Lorem ipsum dolor sit amet. Eos voluptatem natus ab vero voluptatum est
    excepturi saepe non minima alias sed laboriosam optio qui dolores autem
    sit quae sequi. Cum dolorem maxime est perferendis dolores aut veritatis
    officia ad voluptas quisquam in consequuntur aperiam qui optio sint.
    """

    name = "Dummy Sparse Regression"

    # Make sure we can run with the current version
    min_benchopt_version = "0.0.0"
    parameters = {
        'reg': [0.05, .1, .5]
    }

    def __init__(self, reg=.1, fit_intercept=False):
        self.reg = reg
        self.fit_intercept = fit_intercept

    def set_data(self, X, y):
        self.X, self.y = X, y
        self.lmbd = self.reg * self._get_lambda_max()

    def skip(self, X, y):
        if np.all(X == 0):
            return True, 'X is all zeros'
        return False, None

    def get_one_result(self):
        return dict(beta=np.zeros(self.X.shape[1]))

    def evaluate_result(self, beta):
        diff = self.y - self.X.dot(beta)
        mse = .5 * diff.dot(diff)
        regularization = abs(beta).sum()
        objective_value = mse + self.lmbd * regularization

        # To test for multiple type of return value, makes this depend on the
        # parameter:
        #   - reg == .1: Return a scalar
        #   - reg < .1: Return a scalar value for `objective_value`
        #   - reg > .1: Return multiple objective values
        if self.reg == .1:
            return objective_value
        elif self.reg < .1:
            return dict(
                regularization=regularization,
                mse=mse,
                value=objective_value,
            )
        else:
            return dict(value=objective_value, val=objective_value * 4)

    def _get_lambda_max(self):
        return abs(self.X.T.dot(self.y)).max()

    def get_objective(self):
        return dict(X=self.X, y=self.y, lmbd=self.lmbd)
