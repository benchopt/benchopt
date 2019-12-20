import numpy as np


# from .datasets import get_boston_data
from .datasets import get_simulated_data


def score_result(X, y, lmbd, beta):
    y_X_beta = y * X.dot(beta.flatten())
    return np.log(1 + np.exp(-y_X_beta)).sum() + lmbd * abs(beta).sum()


DATASETS = {
    'simulated': (
        get_simulated_data, dict(n_samples=100, n_features=5000, reg=.1)
    ),
    # 'boston': (
    #     get_boston_data, dict(reg=.1)
    # )
}
