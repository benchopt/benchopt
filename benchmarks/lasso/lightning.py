from lightning.regression import CDRegressor


from benchopt.base import BaseSolver


class Solver(BaseSolver):
    name = 'Lightning'

    parameters = dict(
        solvers=['saga', 'liblinear']
    )

    def set_loss(self, X, y, lmbd):
        self.X = X
        self.y = y
        self.lmbd = lmbd

        self.clf = CDRegressor(
            loss='squared', penalty='l1', C=1, alpha=self.lmbd,
            tol=1e-15, shrinking=False)

    def run(self, n_iter):
        self.clf.max_iter = n_iter
        self.clf.fit(self.X, self.y)

    def get_result(self):
        print(self.clf.coef_.flatten())
        return self.clf.coef_.flatten()
