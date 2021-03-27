from benchopt import BaseSolver, safe_import_context

with safe_import_context() as import_ctx:
    import numpy as np


class Solver(BaseSolver):
    name = 'Python-PGD'  # proximal gradient, optionally accelerated

    # Any parameter defined here is accessible as an attribute of the solver.
    parameters = {'step_size': [1, 1.5]}

    # Store the information to compute the objective. The parameters of this
    # function are the eys of the dictionary obtained when calling
    # ``Objective.to_dict``.
    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd

    # Main function of the solver, which compute a solution estimate.
    # Here this is the proximal gradient descent.
    def run(self, n_iter):
        L = np.linalg.norm(self.X, ord=2) ** 2
        step_size = self.step_size / L
        mu = step_size * self.lmbd

        n_features = self.X.shape[1]
        w = np.zeros(n_features)

        for _ in range(n_iter):
            w -= step_size * self.X.T @ (self.X @ w - self.y)
            w -= np.clip(w, -mu, mu)

        self.w = w

    # Return the solution estimate computed.
    def get_result(self):
        return self.w
