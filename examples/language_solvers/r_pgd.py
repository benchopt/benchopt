from pathlib import Path

from benchopt import BaseSolver

import numpy as np

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

    parameters = {'lr': [1e-3, 1e-2]}

    def set_objective(self, X):
        self.X = X
        robjects = import_func_from_r_file(R_FILE)
        self.r_gd = robjects.r['gradient_descent']

    def run(self, n_iter):
        with converter_ctx():
            coefs = self.r_gd(
                self.X, self.lr, n_iter=n_iter
            )
            self.X_hat = np.asarray(coefs)

    def get_result(self):
        return {'X_hat': self.X_hat}
