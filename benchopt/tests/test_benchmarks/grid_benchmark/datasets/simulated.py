import numpy as np

from benchopt import BaseDataset
from benchopt.datasets import make_correlated_data


class Dataset(BaseDataset):

    name = "Simulated"
    __name__ = 'test'

    parameters = {
        'n_samples, n_features': [
            (100, 200)
        ],
        'rho': [0],
    }

    def __init__(self, n_samples=10, n_features=50,  rho=0.6, random_state=27):
        self.n_samples = n_samples
        self.n_features = n_features
        self.random_state = random_state
        self.rho = rho

    def get_data(self):
        rng = np.random.RandomState(self.random_state)

        X, y, _ = make_correlated_data(self.n_samples, self.n_features,
                                       rho=self.rho, random_state=rng)

        return dict(X=X, y=y)
