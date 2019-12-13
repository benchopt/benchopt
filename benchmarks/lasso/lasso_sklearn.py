from sklearn.linear_model import Lasso


from benchopt.base import Solver


class SkLasso(Solver):
    name = 'sklearn'

    def set_loss(self, X, y, lmbd):
        self.X = X
        self.y = y
        self.lmbd = lmbd

        n_samples = X.shape[0]
        self.clf = Lasso(alpha=lmbd/n_samples, fit_intercept=False, tol=0)

    def run(self, n_iter):
        self.clf.max_iter = n_iter
        self.clf.fit(self.X, self.y)

    def get_result(self):
        return self.clf.coef_
