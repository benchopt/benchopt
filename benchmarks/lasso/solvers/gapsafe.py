import numpy as np

from benchopt.base import BaseSolver
from benchopt.util import safe_import


with safe_import():
    from gsroptim.lasso import lasso_path  # TODO make it available in init?


class Solver(BaseSolver):
    name = 'Gapsafe'
    sampling_strategy = 'iteration'

    install_cmd = 'pip'
    requirements = ['gsroptim']
    requirements_install = [
        'git+https://github.com/EugeneNdiaye/Gap_Safe_Rules.git']

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd

    def run(self, n_iter):
        coefs_ = lasso_path(
            self.X, self.y, [self.lmbd], max_iter=n_iter, eps=1e-14)
        self.coef_ = coefs_[:, -1]

    def get_result(self):
        return self.coef_
