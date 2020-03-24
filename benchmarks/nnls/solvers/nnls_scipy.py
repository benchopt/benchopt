from benchopt.base import BaseSolver
from benchopt.util import safe_import


with safe_import() as solver_import:
    from scipy import optimize


class Solver(BaseSolver):
    name = 'scipy'

    install_cmd = 'pip'
    requirements = ['scipy']

    def set_objective(self, X, y):
        self.X, self.y = X, y

    def run(self, n_iter):
        # XXX HACK scipy: when maxiter < 10 could get a
        # RuntimeError: too many iterations
        self.w = optimize.nnls(self.X, self.y, maxiter=n_iter + 10)[0]

    def get_result(self):
        return self.w
