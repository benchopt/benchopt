import blitzl1

from benchopt.base import BaseSolver


class Solver(BaseSolver):
    name = 'Blitz'
    sampling_strategy = 'tolerance'

    def set_loss(self, loss_parameters):
        self.X, self.y, self.lmbd = loss_parameters

        # n_samples = self.X.shape[0]
        # self.lmbd /= n_samples

        blitzl1.set_use_intercept(False)
        self.problem = blitzl1.LassoProblem(self.X, self.y)

    def run(self, n_iter):
        blitzl1.set_tolerance(1e-1 / n_iter)
        self.coef_ = self.problem.solve(self.lmbd).x

    def get_result(self):
        return self.coef_.flatten()
