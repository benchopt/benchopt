from lightning.regression import CDRegressor


from benchopt.base import BaseSolver


class Solver(BaseSolver):
    name = 'Lightning'

    parameters = dict(
        solvers=['saga', 'liblinear']
    )

    def set_loss(self, loss_parameters):
        self.X, self.y, self.lmbd = loss_parameters

        self.clf = CDRegressor(
            loss='squared', penalty='l1', C=1, alpha=self.lmbd,
            tol=1e-15, shrinking=False)

    def run(self, n_iter):
        self.clf.max_iter = n_iter
        self.clf.fit(self.X, self.y)

    def get_result(self):
        return self.clf.coef_.flatten()
