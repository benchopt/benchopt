from benchopt import BaseDataset

import numpy as np


class Dataset(BaseDataset):
    # Name of the Dataset, used to select it in the CLI
    name = 'simulated'

    # ``get_data()`` is the only method a dataset should implement.
    def get_data(self):
        """Load the data for this Dataset.

        Usually, the data are either loaded from disk as arrays or Tensors,
        or a dataset/dataloader object is used to allow the models to load
        the data in more flexible forms (e.g. with mini-batches).

        The dictionary's keys are the kwargs passed to ``Objective.set_data``.
        """
        return dict(X=np.random.randn(10, 2))
