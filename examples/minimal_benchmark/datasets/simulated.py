from benchopt import BaseDataset
import numpy as np


class Dataset(BaseDataset):
    name = 'simulated'

    def get_data(self):
        return dict(X=np.random.randn(10, 2))
