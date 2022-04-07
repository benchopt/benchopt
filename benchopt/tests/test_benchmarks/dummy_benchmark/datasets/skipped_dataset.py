import numpy as np

from benchopt import BaseDataset


class Dataset(BaseDataset):

    name = "Skipped-Dataset"

    # List of parameters to generate the datasets. The benchmark will consider
    # the cross product for each key in the dictionary.
    parameters = {}

    def get_data(self):
        X = np.zeros((2, 2))
        y = np.zeros((2,))
        data = dict(X=X, y=y)
        return 2, data
