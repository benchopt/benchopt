import numpy as np
from scipy import sparse
from bz2 import BZ2Decompressor
from os.path import join as pjoin

from download import download
from sklearn.datasets import load_svmlight_file

from benchopt.config import get_global_setting


DATA_DIR = get_global_setting('cache_dir')

NAMES = {'rcv1_train': 'binary/rcv1_train.binary',
         'news20': 'binary/news20.binary',
         'finance': 'regression/log1p.E2006.train',
         'kdda_train': 'binary/kdda'}

N_FEATURES = {'finance': 4272227,
              'news20': 1355191,
              'rcv1_train': 47236,
              'kdda_train': 20216830}


def download_libsvm(X_path, y_path, name, replace=False):
    url = ("https://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/" +
           NAMES[name] + ".bz2")
    path = download(url, pjoin(DATA_DIR, name), replace=replace)

    decompressor = BZ2Decompressor()
    with (open(pjoin(path, NAMES[name].split('/')[-1]), "r+b") as f,
          open(path, "rb") as g):
        for data in iter(lambda: g.read(100 * 1024), b''):
            f.write(decompressor.decompress(data))

        X, y = load_svmlight_file(f, N_FEATURES[names])
        X = sparse.csc_matrix(X)
        X.sort_indices()
        sparse.save_npz(X_PATH, X)
        np.save(Y_PATH, y)
    return X, y
