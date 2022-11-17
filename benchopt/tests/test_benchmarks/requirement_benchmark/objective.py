from benchopt.base import BaseObjective
from benchopt import safe_import_context

with safe_import_context() as import_ctx:
    import numpy as np
    import dummy_package


class Objective(BaseObjective):
    name = "Test objective requirements"

    install_cmd = 'conda'
    requirements = ['pip:git+https://github.com/tommoral/dummy_package']

    def __init__(self):
        pass

    def set_data(self, X):
        self.X = X

    def get_one_solution(self):
        return np.zeros(self.X.shape[1])

    def compute(self, beta):
        dummy_package.__version__  # make sure this was imported
        Xb = self.X @ beta
        return .5 * Xb.T.dot(Xb)

    def get_objective(self):
        return dict(X=self.X)
