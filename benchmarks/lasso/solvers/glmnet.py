import numpy as np

from benchopt.base import BaseSolver
from benchopt.util import safe_import


with safe_import() as solver_import:
    import rpy2.robjects.packages as rpackages
    from rpy2 import robjects
    from rpy2.robjects import numpy2ri


class Solver(BaseSolver):
    name = "glmnet"

    install_cmd = 'bash'
    install_script = 'install_glmnet.sh'
    requirements = ['rpy2']

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd
        self.lmbd_max = np.max(np.abs(X.T @ y))

    def run(self, tol):
        numpy2ri.activate()
        rpackages.importr('glmnet')
        glmnet = robjects.r['glmnet']
        fit_dict = {"lambda.min.ratio": self.lmbd / self.lmbd_max}
        glmnet_fit = glmnet(self.X, self.y, intercept=False,
                            standardize=False, thresh=tol, **fit_dict)
        results = dict(zip(glmnet_fit.names, list(glmnet_fit)))
        as_matrix = robjects.r['as']
        coefs = np.array(as_matrix(results["beta"], "matrix"))
        self.w = coefs[:, -1]
        # TODO del coefs?

    def get_result(self):
        return self.w
