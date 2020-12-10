import numpy as np
from pathlib import Path

from benchopt import BaseSolver
from benchopt import safe_import_context


with safe_import_context() as import_ctx:

    from rpy2 import robjects
    from rpy2.robjects import numpy2ri
    from benchopt.helpers.r_lang import import_func_from_r_file

    # Setup the system to allow rpy2 running
    R_FILE = str(Path(__file__).with_suffix('.R'))
    import_func_from_r_file(R_FILE)
    numpy2ri.activate()


class Solver(BaseSolver):
    name = "R-PGD"

    install_cmd = 'conda'
    requirements = ['r-base', 'rpy2']
    stop_strategy = 'iteration'
    support_sparse = False

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd
        self.lmbd_max = np.max(np.abs(X.T @ y))
        self.r_pgd = robjects.r['proximal_gradient_descent']

    def run(self, n_iter):

        # There is an issue in loading Lapack library with rpy2 so
        # we cannot compute the SVD in R for now. We compute it using
        # numpy but this should be fixed at some point. See issue #52
        step_size = 1 / np.linalg.norm(self.X, ord=2) ** 2
        coefs = self.r_pgd(
            self.X, self.y[:, None], self.lmbd,
            step_size=step_size, n_iter=n_iter
        )
        as_matrix = robjects.r['as']
        self.w = np.array(as_matrix(coefs, "matrix"))

    def get_result(self):
        return self.w.flatten()
