from benchopt import BaseObjective
import numpy as np


class Objective(BaseObjective):
    name = 'minimal-objective'

    def set_data(self, X):
        self.X = X

    def get_objective(self):
        return dict(X=self.X)

    def evaluate_result(self, X_hat):
        return dict(value=np.linalg.norm(self.X - X_hat))

    def get_one_result(self):
        return dict(X_hat=1)
