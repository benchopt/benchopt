from sklearn.linear_model import LogisticRegression


from benchopt.base import Solver


class SkLogreg(Solver):
    name = 'sklearn'

    parameters = dict(
        solvers=['saga', 'liblinear']
    )

    def set_loss(self, X, y, lmbd):
        self.X = X
        self.y = y
        self.lmbd = lmbd

        self.clf = LogisticRegression(
            solver='saga',
            C=lmbd, penalty='l1', fit_intercept=False, tol=1e-12)

    def run(self, n_iter):
        self.clf.max_iter = n_iter
        self.clf.fit(self.X, self.y)

    def get_result(self):
        return self.clf.coef_.T
