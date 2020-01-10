from benchopt.base import BaseSolver
from benchopt.util import safe_import


with safe_import() as solver_import:
    from celer.homotopy import celer_path


class Solver(BaseSolver):
    name = 'Celer'

    install_cmd = 'pip'
    package_name = 'celer'
    package_install = 'git+https://github.com/mathurinm/celer.git'

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd

        self.solver_parameter = dict(
            solver='celer', max_epochs=50000, p0=10, gap_freq=10,
            use_accel=True, tol=1e-12, prune=True, better_lc=True
        )

    def run(self, n_iter):
        path = celer_path(self.X, self.y, pb="logreg", alphas=[self.lmbd],
                          max_iter=n_iter, **self.solver_parameter)
        self.coef_ = path[1]

    def get_result(self):
        return self.coef_.flatten()
