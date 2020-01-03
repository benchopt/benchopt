import numpy as np


def loss_function(X, y, lmbd, beta):
    y_X_beta = y * X.dot(beta.flatten())
    return np.log(1 + np.exp(-y_X_beta)).sum() + lmbd * abs(beta).sum()
