from benchopt.base import BaseSolver
from benchopt.util import safe_import_context


with safe_import_context() as import_ctx:
    from cyanure import BinaryClassifier


class Solver(BaseSolver):
    name = 'Cyanure'

    install_cmd = 'conda'
    requirements = ['pip:cyanure-mkl']

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd

        self.solver = BinaryClassifier(loss='logistic', penalty='l1',
                                       fit_intercept=False)
        self.solver_parameter = dict(
            lambd=self.lmbd / self.X.shape[0],
            tol=1e-12, verbose=False
        )

    def run(self, n_iter):
        self.solver.fit(self.X, self.y, max_epochs=n_iter,
                        **self.solver_parameter)

    def get_result(self):
        return self.solver.get_weights()
