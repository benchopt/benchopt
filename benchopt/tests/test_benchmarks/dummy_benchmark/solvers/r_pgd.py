from pathlib import Path

from benchopt import BaseSolver
from benchopt import safe_import_context


with safe_import_context() as import_ctx:
    import numpy as np

    # Import helpers from rpy2 and benchopt.helpers.r_lang
    from rpy2 import robjects
    from rpy2.robjects import numpy2ri
    from benchopt.helpers.r_lang import import_func_from_r_file

    # Setup the system to allow passing numpy arrays to rpy2
    numpy2ri.activate()

    # Import R function defined in r_pgd.R so they can be retrieved as python
    # functions using `func = robjects.r['FUNC_NAME']`
    R_FILE = str(Path(__file__).with_suffix('.R'))
    import_func_from_r_file(R_FILE)


class Solver(BaseSolver):
    name = "R-PGD"

    install_cmd = 'conda'
    requirements = ['r-base', 'rpy2']
    stop_strategy = 'iteration'
    support_sparse = False

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd
        self.r_pgd = robjects.r['proximal_gradient_descent']

    def run(self, n_iter):
        coefs = self.r_pgd(self.X, self.y[:, None], self.lmbd, n_iter=n_iter)
        self.w = np.asarray(coefs)

    def get_result(self):
        return self.w.flatten()
