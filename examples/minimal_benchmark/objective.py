from benchopt import BaseObjective
import numpy as np


class Objective(BaseObjective):
    # Name of the Objective function
    name = 'Quadratic'

    # The three methods below define the links between the Dataset,
    # the Objective and the Solver.
    def set_data(self, X):
        """Set the data from a Dataset to compute the objective.

        The argument are the keys of the dictionary returned by
        ``Dataset.get_data``.
        """
        self.X = X

    def get_objective(self):
        "Returns a dict passed to ``Solver.set_objective`` method."
        return dict(X=self.X)

    def evaluate_result(self, X_hat):
        """Compute the objective value(s) given the output of a solver.

        The arguments are the keys in the dictionary returned
        by ``Solver.get_result``.
        """
        return dict(value=np.linalg.norm(self.X - X_hat))

    def get_one_result(self):
        """Return one solution for which the objective can be evaluated.

        This function is mostly used for testing and debugging purposes.
        """
        return dict(X_hat=1)
