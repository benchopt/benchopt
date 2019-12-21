from blitzl1 import LassoProblem

from benchopt.base import BaseSolver


class Solver(BaseSolver):
    name = 'Blitz'

    def set_loss(self, loss_parameters):
        self.X, self.y, self.lmbd = loss_parameters

        self.problem = LassoProblem(self.X, self.y)

    def run(self, n_iter):
        self.coef_ = self.problem.solve(self.lmbd)

    def get_result(self):
        return self.coef_.flatten()
