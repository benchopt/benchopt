import warnings


from benchopt.base import BaseSolver
from benchopt.util import safe_import


with safe_import() as solver_import:
    from sklearn.exceptions import ConvergenceWarning
    from sklearn.linear_model import LogisticRegression


class Solver(BaseSolver):
    name = 'sklearn'

    install_cmd = 'pip'
    package_name = 'scikit-learn'
    package_import = 'sklearn'

    parameters = {
        'solver': [
            # 'saga',
            'liblinear'],
    }
    parameter_template = "{solver}"

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd

        warnings.filterwarnings('ignore', category=ConvergenceWarning)

        self.clf = LogisticRegression(
            solver=self.solver, C=1 / self.lmbd,
            penalty='l1', fit_intercept=False,
            tol=1e-12)

    def run(self, n_iter):
        self.clf.max_iter = n_iter
        self.clf.fit(self.X, self.y)

    def get_result(self):
        return self.clf.coef_.T
