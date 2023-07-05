from benchopt import BaseObjective, safe_import_context

with safe_import_context() as import_ctx:
    import numpy as np


class Objective(BaseObjective):

    name = "Lasso path fitting"

    min_benchopt_version = "1.4.0"
    parameters = {
        'lmbd_ratio_max': [1e-0],
        'lmbd_ratio_min': [1e-2],
        'lmbd_ratio_num': [20],
    }

    def set_data(self, X, y):
        self.X, self.y = X, y
        self.lmbd_grid = np.logspace(
            np.log10(self.lmbd_ratio_max),
            np.log10(self.lmbd_ratio_min),
            self.lmbd_ratio_num,
        ) * np.linalg.norm(self.X.T @ self.y, np.inf)

    def get_one_solution(self):
        return np.zeros(self.X.shape[1])

    def compute(self, result):
        beta, lmbd_index = result
        lmbd = self.lmbd_grid[lmbd_index]
        value = (
            0.5 * np.linalg.norm(self.y - self.X @ beta) +
            lmbd * np.linalg.norm(beta, 1)
        )
        return dict(value=value)

    def get_objective(self):
        return dict(X=self.X, y=self.y, lmbd_grid=self.lmbd_grid)
