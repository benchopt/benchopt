import warnings

from benchopt.base import BaseSolver
from benchopt.util import safe_import


with safe_import() as solver_import:
    from celer import LogisticRegression
    from celer.homotopy import ConvergenceWarning


class Solver(BaseSolver):
    name = 'Celer'
    sampling_strategy = 'iteration'

    install_cmd = 'pip'
    requirements = ['celer']
    requirements_install = ['git+https://github.com/mathurinm/celer.git']

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd

        warnings.filterwarnings('ignore', category=ConvergenceWarning)
        self.clf = LogisticRegression(
            penalty='l1', C=1/self.lmbd, max_iter=1,
            max_epochs=100000, p0=10, verbose=False, tol=1e-12,
            fit_intercept=False
        )

    def run(self, n_iter):
        self.clf.max_iter = n_iter
        self.clf.fit(self.X, self.y)

    def get_result(self):
        return self.clf.coef_.flatten()
