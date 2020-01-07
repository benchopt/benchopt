import numpy as np
from scipy import sparse
from os.path import join as pjoin

from benchopt.base import BaseDataset
from benchopt.config import get_global_setting
from benchopt.dataset_util import download_libsvm

DATA_DIR = get_global_setting('cache_dir')


class Dataset(BaseDataset):
    # TODO call the dataset log1p_train to harmonize with libsvm naming?
    name = "finance"
    X_PATH = pjoin(DATA_DIR, name, "X.npz")
    Y_PATH = pjoin(DATA_DIR, name, "y.npy")

    def get_data(self):
        try:
            X = sparse.load_npz(X_PATH)
            y = np.load(Y_PATH)
        except FileNotFoundError:
            X, y = download_libsvm(X_PATH, Y_PATH, name)

        data = dict(X=X, y=y)

        return X.shape[1], data
