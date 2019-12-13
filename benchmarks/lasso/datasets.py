import numpy as np


def get_simulated_data(n_samples=100, n_features=5000, reg=.1):
    X = np.random.randn(n_samples, n_features)
    y = np.random.randn(n_samples)

    lmbd_max = abs(X.T.dot(y)).max()
    lmbd = reg * lmbd_max
    return X, y, lmbd
