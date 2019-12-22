import numpy as np
from sklearn.datasets import load_boston


def get_lmbd_max(X, y):
    return abs(X.T.dot(y)).max()


def get_simulated_data(n_samples=100, n_features=5000, reg=.1,
                       random_state=27):

    rng = np.random.RandomState(random_state)
    X = rng.randn(n_samples, n_features)
    y = rng.randn(n_samples)

    lmbd = reg * get_lmbd_max(X, y)

    return n_features, X, y, lmbd


def get_boston_data(reg=.1):
    X, y = load_boston(return_X_y=True)

    lmbd = reg * get_lmbd_max(X, y)

    return X.shape[1], X, y, lmbd
