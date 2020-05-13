import os
import numpy as np

from benchopt.base import BaseDataset
from benchopt.config import get_global_setting
from benchopt.util import safe_import

with safe_import():
    # Dependencies of download_libsvm are scikit-learn, download and tqdm
    from benchopt.utils.datasets.libsvm import download_libsvm
    from scipy import sparse

DATA_DIR = get_global_setting('data_dir')


class Dataset(BaseDataset):
    # TODO call the dataset log1p_train to harmonize with libsvm naming?
    name = "finance"

    install_cmd = 'conda'
    requirements = ['scikit-learn', 'scipy', 'download', 'tqdm']
    requirements_import = ['sklearn', 'scipy', 'download', 'tqdm']

    def get_data(self):

        X_path = os.path.join(DATA_DIR, self.name, "X.npz")
        y_path = os.path.join(DATA_DIR, self.name, "y.npy")

        try:
            X = sparse.load_npz(X_path)
            y = np.load(y_path)
        except FileNotFoundError:
            X, y = download_libsvm(X_path, y_path, self.name)

        data = dict(X=X, y=y)

        return X.shape[1], data
