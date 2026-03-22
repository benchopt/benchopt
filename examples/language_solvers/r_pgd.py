from pathlib import Path

from benchopt import BaseSolver

import numpy as np
from scipy.sparse import issparse

# Import helpers from rpy2 and benchopt.helpers.r_lang
from benchopt.helpers.r_lang import import_func_from_r_file, converter_ctx

# Import R function defined in r_pgd.R so they can be retrieved as python
# functions using `func = robjects.r['FUNC_NAME']`
R_FILE = str(Path(__file__).with_suffix('.R'))


class Solver(BaseSolver):
    name = "R-PGD"

    install_cmd = 'conda'
    requirements = ['r-base', 'rpy2']
    sampling_strategy = 'iteration'

    def skip(self, X, y, lmbd):
        if issparse(X):
            return True, "does not support sparse X"
        return False, None

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd
        robjects = import_func_from_r_file(R_FILE)
        self.r_pgd = robjects.r['proximal_gradient_descent']

    def run(self, n_iter):
        with converter_ctx():
            coefs = self.r_pgd(
                self.X, self.y[:, None], self.lmbd, n_iter=n_iter
            )
            self.w = np.asarray(coefs)

    def get_result(self):
        return {'beta': self.w.flatten()}
