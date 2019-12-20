from cyanure import Regression

from benchopt.base import BaseSolver


class Solver(BaseSolver):
    name = 'Cyanure'

    def set_loss(self, X, y, lmbd):
        self.X = X
        self.y = y
        self.lmbd = lmbd

        n_samples = X.shape[0]

        self.solver = Regression(loss='square', penalty='l1',
                                 fit_intercept=False)
        self.solver_parameter = dict(
            lambd=self.lmbd / n_samples, solver='auto',
            tol=1e-12, verbose=False
        )

    def run(self, n_iter):
        self.solver.fit(self.X, self.y, max_epochs=n_iter,
                        **self.solver_parameter)

    def get_result(self):
        return self.solver.get_weights().flatten()
