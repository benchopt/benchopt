import numpy as np
from benchopt import BaseObjective


class Objective(BaseObjective):
    # Name of the Objective function
    name = "Lasso Regression"

    # parametrization of the objective with various regularization parameters.
    # All parameters `p` defined here will be accessible as `self.p`.
    parameters = {
        'reg': [0.05, .1, .5]
    }

    def get_one_result(self):
        "Return one solution for which the objective can be evaluated."
        return np.zeros(self.X.shape[1])

    def _get_lambda_max(self):
        "Helper to compute the scaling of lambda on the given data."
        return abs(self.X.T @ self.y).max()

    def set_data(self, X, y):
        """Set the data from a Dataset to compute the objective.

        The argument are the keys in the data dictionary returned by
        get_data.
        """
        self.X, self.y = X, y
        self.lmbd = self.reg * self._get_lambda_max()

    def evaluate_result(self, beta):
        """Compute the objective value given the output of a solver.

        The arguments are the keys in the result dictionary returned
        by ``Solver.get_result``.
        """
        diff = self.y - self.X @ beta
        objective_value = .5 * diff @ diff + self.lmbd * abs(beta).sum()
        return objective_value  # or return dict(value=objective_value)

    def get_objective(self):
        "Returns a dict to pass to the set_objective method of a solver."
        return dict(X=self.X, y=self.y, lmbd=self.lmbd)
