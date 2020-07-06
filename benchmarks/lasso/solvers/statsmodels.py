from benchopt.base import BaseSolver
from benchopt.util import safe_import_context


with safe_import_context() as import_ctx:
    import statsmodels.api as sm


class Solver(BaseSolver):
    name = 'statsmodels'

    install_cmd = 'conda'
    requirements = ['statsmodels']

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd
        self.n_samples = self.X.shape[0]
        self.clf = sm.GLS(y, X, hasconst=False)

    def run(self, n_iter):

        self.results = self.clf.fit_regularized(
            alpha=self.lmbd / self.n_samples, method='elastic_net',
            L1_wt=1, maxiter=n_iter, cnvrg_tol=1e-14, zero_tol=1e-14
        )

    def get_result(self):
        return self.results.params.flatten()
