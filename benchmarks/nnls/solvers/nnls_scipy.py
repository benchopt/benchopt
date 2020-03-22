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
        self.w = optimize.nnls(self.X, self.y, maxiter=n_iter)[0]

    def get_result(self):
        return self.w
