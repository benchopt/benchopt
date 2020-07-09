from benchopt.base import BaseSolver
from benchopt.util import safe_import_context


with safe_import_context() as import_ctx:
    from lightning.classification import CDClassifier


class Solver(BaseSolver):
    name = 'Lightning'

    install_cmd = 'conda'
    requirements = [
        'pip:git+https://github.com/scikit-learn-contrib/lightning.git'
    ]

    def set_objective(self, X, y, lmbd):

        self.X, self.y, self.lmbd = X, y, lmbd

        self.clf = CDClassifier(
            loss='log', penalty='l2', C=1, alpha=self.lmbd,
            tol=0, permute=False, shrinking=False, warm_start=False)

    def run(self, n_iter):
        self.clf.max_iter = n_iter
        self.clf.fit(self.X, self.y)

    def get_result(self):
        return self.clf.coef_.flatten()
