import numpy as np

from benchopt.base import BaseSolver
from benchopt.util import safe_import


with safe_import():
    from gsroptim.lasso import lasso_path  # TODO make it available in init?


class Solver(BaseSolver):
    name = 'Gap Safe'
    sampling_strategy = 'iteration'

    install_cmd = 'pip'
    requirements = ['gsroptim']
    requirements_install = [
        'git+https://github.com/EugeneNdiaye/Gap_Safe_Rules.git']

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd
        self.lmbd_max = np.max(np.abs(X.T @ y))

    def run(self, n_iter):
        # TODO determine optimal strategy to solve single lambda.
        # Right now, take a geom grid of 100 lambdas from lmb_max
        # to lmbd
        lmbds = self.lmbd_max * np.geomspace(1, self.lmbd / self.lmbd_max,
                                             num=100)
        coefs_ = lasso_path(self.X, self.y, lmbds, max_iter=n_iter)
        self.coef_ = coefs_[:, -1]

    def get_result(self):
        return self.coef_
