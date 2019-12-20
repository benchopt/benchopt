import warnings

from sklearn.linear_model import Lasso
from sklearn.exceptions import ConvergenceWarning


from benchopt.base import BaseSolver


class Solver(BaseSolver):
    name = 'sklearn'

    def set_loss(self, X, y, lmbd):
        self.X = X
        self.y = y
        self.lmbd = lmbd

        n_samples = X.shape[0]
        self.clf = Lasso(alpha=lmbd/n_samples, fit_intercept=False, tol=0)
        warnings.filterwarnings('ignore', category=ConvergenceWarning)

    def run(self, n_iter):
        self.clf.max_iter = n_iter
        self.clf.fit(self.X, self.y)

    def get_result(self):
        return self.clf.coef_.flatten()
