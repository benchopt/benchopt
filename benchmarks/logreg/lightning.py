from lightning.classification import CDClassifier


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

        self.clf = CDClassifier(
            loss='log', penalty='l1', C=1, alpha=self.lmbd,
            tol=1e-12)

    def run(self, n_iter):
        self.clf.max_iter = n_iter
        self.clf.fit(self.X, self.y)

    def get_result(self):
        return self.clf.coef_.T
