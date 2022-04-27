from benchopt.base import BaseObjective


class Objective(BaseObjective):
    name = "Test simulated test configurations"

    def __init__(self):
        pass

    def set_data(self, X):
        self.X = X

    def compute(self, beta):
        Xb = self.X @ beta
        return .5 * Xb.T.dot(Xb)

    def to_dict(self):
        return dict(X=self.X)
