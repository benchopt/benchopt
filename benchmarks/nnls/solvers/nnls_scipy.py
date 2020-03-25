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
        # Passing n_iter as in:
        # optimize.nnls(self.X, self.y, maxiter=n_iter)
        # is not done here as it has apparently no impact
        # on convergence and is just used to raise a RuntimeError
        # if the number of iterations actually run exceeds n_iter.
        # This avoids producing errors on various datasets such
        # as Boston.
        self.w = optimize.nnls(self.X, self.y)[0]

    def get_result(self):
        return self.w
