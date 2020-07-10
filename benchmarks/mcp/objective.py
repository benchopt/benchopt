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
        'reg': [[.1, 1.2], [.5, 1.2]]  # [lbda ratio, gamma
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
        norms2 = (self.X ** 2).sum(axis=0)
        n_samples = len(self.y)
        diff = self.y - self.X.dot(beta)
        beta_norm = np.sqrt(norms2 / n_samples) * beta

        pen = (self.gamma * self.lmbd ** 2 / 2.) * np.ones(beta_norm.shape)
        small_idx = np.abs(beta_norm) <= self.gamma * self.lmbd
        pen[small_idx] = self.lmbd * np.abs(beta_norm[small_idx]) - beta_norm[small_idx] ** 2 / (2 * self.gamma)

        return diff.dot(diff) / (2. * n_samples) + pen.sum()

    def _get_lambda_max(self):
        # Possibly to adapt for MCP, but good enough for a V1 scaling of lmbd.
        norms2 = (self.X ** 2).sum(axis=0)
        n_samples, _ = self.X.shape
        return abs(self.X.T.dot(self.y) / (n_samples * norms2)**0.5).max()
        # return abs(self.X.T.dot(self.y) / len(self.y)).max()

    def to_dict(self):
        return dict(X=self.X, y=self.y, lmbd=self.lmbd, gamma=self.gamma)
        #           fit_intercept=self.fit_intercept)
