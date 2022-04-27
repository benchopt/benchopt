from benchopt import BaseDataset
from benchopt import safe_import_context


with safe_import_context() as import_ctx:
    import numpy as np


class Dataset(BaseDataset):
    name = "Simulated"

    test_parameters = {
        'n_samples': [0, 10],
    }

    def get_data(self):
        return 10, dict(X=np.random.randn(self.n_samples, 10))
