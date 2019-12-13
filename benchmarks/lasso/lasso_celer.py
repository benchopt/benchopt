from celer import Lasso

from benchopt.base import Solver


class Celer(Solver):
    name = 'Celer'

    def set_loss(self, X, y, lmbd):
        self.X = X
        self.y = y
        self.lmbd = lmbd

        n_samples = X.shape[0]
        self.lasso = Lasso(
            alpha=self.lmbd/n_samples, max_iter=1, gap_freq=10,
            max_epochs=100000, p0=10, verbose=False, tol=1e-12, prune=0,
            fit_intercept=False, normalize=False, warm_start=False,
            positive=False
        )

    def run(self, n_iter):
        self.lasso.max_iter = n_iter
        self.lasso.fit(self.X, self.y)

    def get_result(self):
        return self.lasso.coef_
