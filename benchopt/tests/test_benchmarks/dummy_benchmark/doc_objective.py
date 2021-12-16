from benchopt.base import BaseObjective


class Objective(BaseObjective):
    # Name of the Objective function
    name = "Lasso Regression"

    # parametrization of the objective with various regularization parameters.
    parameters = {
        'reg': [0.05, .1, .5]
    }

    def __init__(self, reg=.1):
        "Store the value of the parameters used to compute the objective."
        self.reg = reg

    def set_data(self, X, y):
        """Set the data from a Dataset to compute the objective.

        The argument are the keys in the data dictionary returned by
        get_data.
        """
        self.X, self.y = X, y
        self.lmbd = self.reg * self._get_lambda_max()

    def to_dict(self):
        "Returns a dict to pass to the set_objective method of a solver."
        return dict(X=self.X, y=self.y, lmbd=self.lmbd)

    def compute(self, beta):
        "Compute the objective value given the output x of a solver."
        diff = self.y - self.X @ beta
        objective_value = .5 * diff @ diff + self.lmbd * abs(beta).sum()
        return objective_value  # or return dict(value=objective_value)

    def _get_lambda_max(self):
        "Helper to compute the scaling of lambda on the given data."
        return abs(self.X.T @ self.y).max()
