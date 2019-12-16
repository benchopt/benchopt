
from .lasso_celer import Celer
from .lasso_sklearn import SkLasso
from .baseline import Baseline


from .datasets import get_boston_data
from .datasets import get_simulated_data


def score_result(X, y, lmbd, beta):
    diff = y - X.dot(beta)
    return .5 * diff.dot(diff) + lmbd * abs(beta).sum()


DATASETS = {
    'simulated': (
        get_simulated_data, dict(n_samples=100, n_features=50000, reg=.1)
    ),
    'boston': (
        get_boston_data, dict(reg=.1)
    )
}

SOLVERS = [Baseline, Celer, SkLasso]
