import numpy as np

from .logreg_celer import Celer
from .logreg_sklearn import SkLogreg
# from .baseline import Baseline


# from .datasets import get_boston_data
from .datasets import get_simulated_data


def score_result(X, y, lmbd, beta):
    y_X_beta = y * X.dot(beta)
    return lmbd * np.log(1 + np.exp(-y_X_beta)).sum() + abs(beta).sum()


DATASETS = {
    'simulated': (
        get_simulated_data, dict(n_samples=100, n_features=50000, reg=.1)
    ),
    # 'boston': (
    #     get_boston_data, dict(reg=.1)
    # )
}

SOLVERS = [Celer, SkLogreg]
# solvers = [Baseline, Celer, SkLasso]
