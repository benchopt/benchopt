
from .lasso_celer import Celer
from .lasso_sklearn import SkLasso
from .baseline import Baseline


from .datasets import get_simulated_data


def score_result(X, y, lmbd, beta):
    diff = y - X.dot(beta)
    return .5 * diff.dot(diff) + lmbd * abs(beta).sum()


datasets = {
    'simulated': (
        get_simulated_data, dict(n_samples=100, n_features=50000, reg=.1)
    )
}

solvers = [Baseline, Celer, SkLasso]


# def benchmark():
#     X, y, lmbd = get_simulated_data(n_samples=100, n_features=50000, reg=.1)

#     res = []
#     for method in [Lasso, Celer, SkLasso]:
#         res.extend(run_one_method(method, 1000, X, y, .1 * lmbd_max))

#     import pandas as pd
#     import matplotlib.pyplot as plt
#     df = pd.DataFrame(res)
#     for m in ['Celer', 'Lasso', 'sklearn']:
#         df_ = df[df.method == m]
#         plt.loglog(df_.time, df_.loss, label=m)
#     plt.legend()
#     plt.show()
