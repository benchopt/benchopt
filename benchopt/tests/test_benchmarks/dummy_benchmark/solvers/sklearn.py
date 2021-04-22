import warnings
from benchopt import BaseSolver
from benchopt import safe_import_context


with safe_import_context() as import_ctx:
    from sklearn.linear_model import Lasso
    from sklearn.exceptions import ConvergenceWarning


class Solver(BaseSolver):
    name = 'sklearn'

    install_cmd = 'conda'
    requirements = ['pip:scikit-learn']

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd

        n_samples = self.X.shape[0]
        self.clf = Lasso(alpha=self.lmbd/n_samples, fit_intercept=False, tol=0)
        warnings.filterwarnings('ignore', category=ConvergenceWarning)

    def run(self, n_iter):
        self.clf.max_iter = n_iter
        self.clf.fit(self.X, self.y)

    def get_result(self):
        return self.clf.coef_.flatten()
