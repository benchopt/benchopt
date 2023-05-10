from benchopt.base import BaseObjective, safe_import_context

# All packages other than benchopt should be imported in this context.
# - This allows to list solvers even when a package is not installed,
#   in particular for listing dependencies to install.
# - This allows to skip imports when listing solvers and datasets
#   for auto completion.
with safe_import_context() as import_ctx:
    import numpy as np


class Objective(BaseObjective):
    # Name of the Objective function
    name = "Lasso Regression"

    # parametrization of the objective with various regularization parameters.
    # All parameters `p` defined here will be accessible as `self.p`.
    parameters = {
        'reg': [0.05, .1, .5]
    }

    def get_one_solution(self):
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

    def compute(self, beta):
        "Compute the objective value given the output x of a solver."
        diff = self.y - self.X @ beta
        objective_value = .5 * diff @ diff + self.lmbd * abs(beta).sum()
        return objective_value  # or return dict(value=objective_value)

    def get_objective(self):
        "Returns a dict to pass to the set_objective method of a solver."
        return dict(X=self.X, y=self.y, lmbd=self.lmbd)
