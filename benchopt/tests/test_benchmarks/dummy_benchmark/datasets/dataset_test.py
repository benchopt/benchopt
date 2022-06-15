import numpy as np

from benchopt import BaseDataset
from benchopt.datasets import make_correlated_data


class Dataset(BaseDataset):

    name = "Test-Dataset"

    # List of parameters to generate the datasets. The benchmark will consider
    # the cross product for each key in the dictionary.
    parameters = {
        'n_samples, n_features': [
            (100, 5000)
        ], 'rho': [0]
    }

    def __init__(
        self,
        n_samples=10,
        n_features=50,
        rho=0.6,
        random_state=27,
        skip=False,
        deprecated_return=False
    ):
        # Store the parameters of the dataset
        self.n_samples = n_samples
        self.n_features = n_features
        self.random_state = random_state
        self.rho = rho
        self.skip = skip
        self.deprecated_return = deprecated_return

    def get_data(self):
        rng = np.random.RandomState(self.random_state)

        X, y, _ = make_correlated_data(self.n_samples, self.n_features,
                                       rho=self.rho, random_state=rng)
        if self.skip:
            X = np.zeros_like(X)
            y = np.zeros_like(y)

        data = dict(X=X, y=y)

        # XXX - Remove in version 1.3
        if self.deprecated_return:
            return self.n_features, data
        else:
            return data
