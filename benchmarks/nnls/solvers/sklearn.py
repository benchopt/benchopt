import warnings
from benchopt.base import BaseSolver
from benchopt.util import safe_import_context

import numpy as np

with safe_import_context() as import_ctx:
    from sklearn.linear_model import Lasso
    from sklearn.exceptions import ConvergenceWarning


class Solver(BaseSolver):
    name = 'sklearn'

    install_cmd = 'conda'
    requirements = ['scikit-learn']

    def set_objective(self, X, y, fit_intercept=False):
        self.X, self.y = np.asfortranarray(X), y
        self.fit_intercept = fit_intercept

        self.clf = Lasso(positive=True, alpha=1e-10,
                         fit_intercept=fit_intercept, tol=0)
        warnings.filterwarnings('ignore', category=ConvergenceWarning)

    def run(self, n_iter):
        self.clf.max_iter = n_iter
        self.clf.fit(self.X, self.y)

    def get_result(self):
        return self.clf.coef_.flatten()
