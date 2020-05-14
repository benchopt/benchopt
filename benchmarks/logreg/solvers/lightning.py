from benchopt.base import BaseSolver
from benchopt.util import safe_import


with safe_import() as solver_import:
    from lightning.classification import CDClassifier


class Solver(BaseSolver):
    name = 'Lightning'

    install_cmd = 'conda'
    requirements = ['pip:sklearn-contrib-lightning']
    requirements_import = ['lightning']
    requirements_install = [
        'pip:git+https://github.com/scikit-learn-contrib/lightning.git'
    ]

    def set_objective(self, X, y, lmbd):

        self.X, self.y, self.lmbd = X, y, lmbd

        self.clf = CDClassifier(
            loss='log', penalty='l1', C=1, alpha=self.lmbd,
            tol=0, permute=False, shrinking=False, warm_start=False)

    def run(self, n_iter):
        self.clf.max_iter = n_iter
        self.clf.fit(self.X, self.y)

    def get_result(self):
        return self.clf.coef_.flatten()
