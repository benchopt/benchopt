from benchopt.base import BaseSolver
from benchopt.util import safe_import_context

with safe_import_context() as import_ctx:
    from sklearn.linear_model import LinearRegression


class Solver(BaseSolver):
    name = 'sklearn'

    install_cmd = 'conda'
    requirements = ['scikit-learn']

    def set_objective(self, X, y, fit_intercept=False):
        self.X, self.y, self.fit_intercept = X, y, fit_intercept
        self.clf = LinearRegression(fit_intercept=fit_intercept)

    def run(self, n_iter):
        self.clf.fit(self.X, self.y)

    def get_result(self):
        return self.clf.coef_.flatten()
