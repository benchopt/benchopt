import os
import numpy as np
from scipy import sparse

from benchopt.base import BaseDataset
from benchopt.config import get_global_setting
from benchopt.dataset_util import download_libsvm

DATA_DIR = get_global_setting('data_dir')


class Dataset(BaseDataset):
    # TODO call the dataset log1p_train to harmonize with libsvm naming?
    name = "finance"
    X_path = os.path.join(DATA_DIR, name, "X.npz")
    y_path = os.path.join(DATA_DIR, name, "y.npy")

    def get_data(self):
        try:
            X = sparse.load_npz(self.X_path)
            y = np.load(self.y_path)
        except FileNotFoundError:
            X, y = download_libsvm(self.X_path, self.y_path, self.name)

        data = dict(X=X, y=y)

        return X.shape[1], data
