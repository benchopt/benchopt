import numpy as np
from scipy import sparse
from bz2 import BZ2Decompressor

from download import download
from sklearn.datasets import load_svmlight_file

from benchopt.base import BaseDataset


class Dataset(BaseDataset):
    # TODO call the dataset log1p_train to harmonize with libsvm naming?
    name = "Finance"
    X_PATH = "foo"  # TODO
    Y_PATH = " foo"  # TODO

    def get_data(self):
        X = sparse.load_npz(X_PATH)
        y = np.load(Y_PATH)
        data = dict(X=X, y=y)

        return X.shape[1], data

    def download_data(self, replace=False):
        url = ("https://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/" +
               "regression/log1p.E2006.train.bz2")
        path = download(url, destination, replace=replace)

        decompressor = BZ2Decompressor()
        with open(decompressed_path, "wb") as f, open(path, "rb") as g:
            for data in iter(lambda: g.read(100 * 1024), b''):
                f.write(decompressor.decompress(data))

        with open(decompressed_path, 'rb') as f:
            X, y = load_svmlight_file(f, 4272227)
            X = sparse.csc_matrix(X)
            X.sort_indices()
            sparse.save_npz(X_PATH, X)
            np.save(Y_PATH, y)
