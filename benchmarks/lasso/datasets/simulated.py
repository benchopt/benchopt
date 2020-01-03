import numpy as np

from benchopt.base import BaseDataset


class Dataset(BaseDataset):

    name = "Simulated"

    parameters = {
        'reg': [.01, .1, .5]
    }

    def __init__(self, n_samples=100, n_features=5000, reg=.1,
                 random_state=27):
        self.n_samples = n_samples
        self.n_features = n_features
        self.reg = reg
        self.random_state = random_state

    def get_loss_parameters(self):

        rng = np.random.RandomState(self.random_state)
        X = rng.randn(self.n_samples, self.n_features)
        y = rng.randn(self.n_samples)

        lmbd = self.reg * self._get_lmbd_max(X, y)

        loss_parameters = dict(X=X, y=y, lmbd=lmbd)

        return self.n_features, loss_parameters

    def _get_lmbd_max(self, X, y):
        return abs(X.T.dot(y)).max()
