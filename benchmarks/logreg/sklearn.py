import warnings

from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression


from benchopt.base import BaseSolver


class Solver(BaseSolver):
    name = 'sklearn'

    parameters = dict(
        solvers=['saga', 'liblinear']
    )

    def set_loss(self, loss_parameters):
        self.X, self.y, self.lmbd = loss_parameters

        warnings.filterwarnings('ignore', category=ConvergenceWarning)

        self.clf = LogisticRegression(
            solver='saga', C=1 / self.lmbd,
            penalty='l1', fit_intercept=False,
            tol=1e-12)

    def run(self, n_iter):
        self.clf.max_iter = n_iter
        self.clf.fit(self.X, self.y)

    def get_result(self):
        return self.clf.coef_.T
