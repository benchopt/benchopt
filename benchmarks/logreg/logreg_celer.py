from celer.homotopy import logreg_path

from benchopt.base import Solver


class Celer(Solver):
    name = 'Celer'

    def set_loss(self, X, y, lmbd):
        self.X = X
        self.y = y
        self.lmbd = lmbd

        self.solver_parameter = dict(
            solver='celer', max_epochs=50000, p0=10, gap_freq=10,
            use_accel=True, tol=1e-12, prune=True, better_lc=True
        )

    def run(self, n_iter):
        path = logreg_path(self.X, self.y, alphas=[self.lmbd], max_iter=n_iter,
                           **self.solver_parameter)
        self.coef_ = path[1]

    def get_result(self):
        return self.coef_
