import os
import numpy as np
from scipy import sparse
from bz2 import BZ2Decompressor

from download import download
from sklearn.datasets import load_svmlight_file

from benchopt.config import get_global_setting


DATA_DIR = get_global_setting('data_dir')

NAMES = {'rcv1_train': 'binary/rcv1_train.binary',
         'news20': 'binary/news20.binary',
         'finance': 'regression/log1p.E2006.train',
         'kdda_train': 'binary/kdda'}

N_FEATURES = {'finance': 4272227,
              'news20': 1355191,
              'rcv1_train': 47236,
              'kdda_train': 20216830}


def download_libsvm(X_path, y_path, name, replace=False):
    file_name = NAMES[name].split('/')[-1]
    url = ("http://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/" +
           NAMES[name] + ".bz2")
    path = download(url, os.path.join(DATA_DIR, name, f"{file_name}.bz2"),
                    replace=replace, progressbar=True)

    # Decompress the files
    decompressor = BZ2Decompressor()
    tmp_path = os.path.join(DATA_DIR, name, file_name)
    with open(tmp_path, "wb") as decompressed_file:
        with open(path, "rb") as orig_file:
            for data in iter(lambda: orig_file.read(100 * 1024), b''):
                decompressed_file.write(decompressor.decompress(data))

    # Read the files with sklearn util
    with open(tmp_path, "rb") as decompressed_file:
        X, y = load_svmlight_file(decompressed_file, N_FEATURES[name])

    os.remove(tmp_path)
    os.remove(path)
    X = sparse.csc_matrix(X)
    X.sort_indices()
    sparse.save_npz(X_path, X)
    np.save(y_path, y)
    return X, y
