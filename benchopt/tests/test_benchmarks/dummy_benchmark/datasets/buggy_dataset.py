import numpy as np
from benchopt import BaseDataset


class Dataset(BaseDataset):
    name = "buggy-dataset"

    parameters = {
        'n_samples, n_featuressss': [
            (100, 5000)
        ],
    }

    def __init__(self, n_samples=10, n_features=50, deprecated_return=False):
        self.n_samples = n_samples
        self.n_features = n_features
        self.deprecated_return = deprecated_return

    def get_data(self):
        X = np.ones((self.n_samples, self.n_features))
        y = np.ones(self.n_samples)

        data = dict(X=X, y=y)

        # XXX - Remove in version 1.3
        if self.deprecated_return:
            return self.n_features, data
        else:
            return data
