import numpy as np

from benchopt.base import BaseDataset


class Dataset(BaseDataset):

    name = "Simulated"

    parameters = {
        'n_samples, n_features': [
            (200, 500),
        ]
    }

    def __init__(self, n_samples=10, n_features=50, random_state=42):
        self.n_samples = n_samples
        self.n_features = n_features
        self.random_state = random_state

    def get_data(self):
        rng = np.random.RandomState(self.random_state)
        X = rng.randn(self.n_samples, self.n_features)
        beta = rng.randn(self.n_features)
        y = np.sign(X.dot(beta))

        data = dict(X=X, y=y)

        return self.n_features, data
