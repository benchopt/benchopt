from benchopt.base import BaseSolver
from benchopt.util import safe_import


with safe_import() as solver_import:
    from lightning.classification import CDClassifier


class Solver(BaseSolver):
    name = 'Lightning'

    install_cmd = 'pip'
    package_name = 'lightning'
    package_install = (
        'git+https://github.com/scikit-learn-contrib/lightning.git'
    )

    parameters = dict(
        solvers=['saga', 'liblinear']
    )

    def set_loss(self, loss_parameters):

        self.X, self.y, self.lmbd = loss_parameters

        self.clf = CDClassifier(
            loss='log', penalty='l1', C=1, alpha=self.lmbd,
            tol=1e-12)

    def run(self, n_iter):
        self.clf.max_iter = n_iter
        self.clf.fit(self.X, self.y)

    def get_result(self):
        return self.clf.coef_.T
