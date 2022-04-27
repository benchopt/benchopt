from benchopt import BaseDataset
from benchopt import safe_import_context


with safe_import_context() as import_ctx:
    import numpy as np


class Dataset(BaseDataset):
    name = "Simulated"

    test_parameters = {
        'n_samples': [1, 10],
    }

    def __init__(self, n_samples=10):
        self.n_samples = 10

    def get_data(self):
        return 10, dict(X=np.random.randn(self.n_samples, 10))
