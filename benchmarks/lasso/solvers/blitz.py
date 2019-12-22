from benchopt.base import BaseSolver
from benchopt.util import safe_import


with safe_import() as solver_import:
    import blitzl1


class Solver(BaseSolver):
    name = 'Blitz'
    sampling_strategy = 'tolerance'

    install_cmd = 'pip'
    install_package = 'blitzl1'
    import_package = 'blitzl1'

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
