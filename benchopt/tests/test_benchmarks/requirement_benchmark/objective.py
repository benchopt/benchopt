from benchopt.base import BaseObjective
from benchopt import safe_import_context

with safe_import_context() as import_ctx:
    import dummy_package


class Objective(BaseObjective):
    name = "Test objective requirements"

    install_cmd = 'conda'
    requirements = ['pip:git+https://github.com/tommoral/dummy_package']

    def __init__(self):
        pass

    def set_data(self, X):
        self.X = X

    def compute(self, beta):
        dummy_package.__version__  # make sure this was imported
        Xb = self.X @ beta
        return .5 * Xb.T.dot(Xb)

    def to_dict(self):
        return dict(X=self.X)
