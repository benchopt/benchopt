from benchopt.base import BaseSolver
from benchopt.util import safe_import_context


with safe_import_context() as import_ctx:
    from lightning.regression import CDRegressor


# TODO: lightning always fit an intercept
#       it is thus not optimizing the same cost function
class Solver(BaseSolver):
    name = 'Lightning'

    install_cmd = 'conda'
    requirements = [
        'pip:git+https://github.com/scikit-learn-contrib/lightning.git'
    ]

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd

        self.clf = CDRegressor(
            loss='squared', penalty='l1', C=1, alpha=self.lmbd,
            tol=1e-15)

    def run(self, n_iter):
        self.clf.max_iter = n_iter
        self.clf.fit(self.X, self.y)

    def get_result(self):
        return self.clf.coef_.flatten()
