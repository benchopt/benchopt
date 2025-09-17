from benchopt import BaseSolver
import numpy as np


class Solver(BaseSolver):
    # Name of the Solver, used to select it in the CLI
    name = 'gd'

    # By default, benchopt will evaluate the result of a method after various
    # number of iterations. Setting the sampling_strategy controls how this is
    # done. Here, we use a callback function that is called at each iteration.
    sampling_strategy = 'callback'

    # Parameters of the method, that will be tested by the benchmark.
    # Each parameter ``param_name`` will be accessible as ``self.param_name``.
    parameters = {'lr': [1e-3, 1e-2]}

    # The three methods below define the necessary methods for the Solver, to
    # get the info from the Objective, to run the method and to return a
    # result that can be evaluated by the Objective.
    def set_objective(self, X):
        """Set the info from a Objective, to run the method.

        This method is also typically used to adapt the solver's parameters to
        the data (e.g. scaling) or to initialize the algorithm.

        The kwargs are the keys of the dictionary returned by
        ``Objective.get_objective``.
        """
        self.X = X
        self.X_hat = np.zeros_like(X)

    def run(self, cb):
        """Run the actual method to benchmark.

        Here, as we use a "callback", we need to call it at each iteration to
        evaluate the result as the procedure progresses.

        The callback implements a stopping mechanism, based on the number of
        iterations, the time and the evoluation of the performances.
        """
        while cb():
            self.X_hat = self.X_hat - self.lr * (self.X_hat - self.X)

    def get_result(self):
        """Format the output of the method to be evaluated in the Objective.

        Returns a dict which is passed to ``Objective.evaluate_result`` method.
        """
        return {'X_hat': self.X_hat}
