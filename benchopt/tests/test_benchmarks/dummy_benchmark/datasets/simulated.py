import numpy as np

from benchopt.base import BaseDataset


class Dataset(BaseDataset):

    name = "Simulated"

    # List of parameters to generate the datasets. The benchmark will consider
    # the cross product for each key in the dictionary.
    parameters = {
        'n_samples, n_features, corr': [
            (100, 5000, 0),
            (100, 5000, 0.6),
            (100, 10000, 0)],  # slow to simulate big correlated design
    }

    def __init__(self, n_samples=10, n_features=50, random_state=27, corr=0):
        # Store the parameters of the dataset
        self.n_samples = n_samples
        self.n_features = n_features
        self.random_state = random_state
        self.corr = corr

    def get_data(self):
        rng = np.random.RandomState(self.random_state)
        if self.corr == 0:
            X = rng.randn(self.n_samples, self.n_features)
        else:
            # use Toeplitz covariance matrix:
            idx = np.arange(self.n_features)
            corr_mat = self.corr ** np.abs(idx[:, None] - idx)
            X = rng.multivariate_normal(
                np.zeros(self.n_features), corr_mat, self.n_samples)

        y = rng.randn(self.n_samples)

        data = dict(X=X, y=y)

        return self.n_features, data
