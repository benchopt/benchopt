import numpy as np


from benchopt.base import BaseObjective


class Objective(BaseObjective):
    """Follows Breheny and Huang 2011, 'coordinate descent algorithms for
    nonconvex penalized regression, with applications to biological
    feature selection' framework.
    """
    name = "MCP Regression"

    parameters = {
        'fit_intercept': [False],
        'reg': [[0.05, 1.2], [.1, 1.2], [.5, 1.2]]  # [lbda ratio, gamma
    }

    def __init__(self, reg=[.1, 1.2], fit_intercept=False):
        self.reg = reg
        self.fit_intercept = fit_intercept
        super().__init__(reg=reg)

    def set_data(self, X, y):
        self.X, self.y = X, y
        self.lmbd = self.reg[0] * self._get_lambda_max()
        self.gamma = self.reg[1]

    def __call__(self, beta):
        diff = self.y - self.X.dot(beta)

        pen = (0.5 * self.gamma * self.lmbd ** 2) * np.ones(beta.shape)
        small_idx = np.abs(beta) < self.gamma * self.lmbd
        pen[small_idx] = self.lmbd * np.abs(beta[small_idx]) - beta[small_idx] ** 2 / (2 * self.gamma)

        return .5 * diff.dot(diff) + pen.sum()

    def _get_lambda_max(self):
        # Possibly to adapt for MCP, but good enough for a V1 scaling of lmbd.
        return abs(self.X.T.dot(self.y)).max()

    def to_dict(self):
        return dict(X=self.X, y=self.y, lmbd=self.lmbd, gamma=self.gamma)
        #           fit_intercept=self.fit_intercept)
