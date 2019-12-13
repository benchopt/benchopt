import time
import numpy as np
from abc import abstractmethod
from collections import namedtuple


Cost = namedtuple('Cost', 'method n_iter time p0'.split(' '))


def get_data(n_samples, n_features):
    X = np.random.randn(n_samples, n_features)
    y = np.random.randn(n_samples)
    return X, y


def score_result(X, y, lmbd, beta):
    diff = y - X.dot(beta)
    return .5 * diff.dot(diff) + lmbd * abs(beta).sum()


def run_one_method(method_class, max_iter, X, y, lmbd):
    method = method_class(X, y, lmbd=lmbd)
    res = []
    list_iter = np.unique(np.logspace(0, np.log10(max_iter), 20, dtype=int))
    for n_iter in list_iter:
        print(f"{n_iter} / {max_iter}")
        t_start = time.time()
        method.run(n_iter=n_iter)
        delta_t = time.time() - t_start
        beta_hat_i = method.get_result()
        p0 = score_result(X, y, lmbd, beta_hat_i)
        res.append(Cost(method=method.name, n_iter=n_iter,
                        time=delta_t, p0=p0))
    return res


class Solver(object):
    name = 'method'

    def __init__(self, X, y, lmbd, **parameters):
        '''Prepare'''
        self.X = X
        self.y = y
        self.lmbd = lmbd

    @abstractmethod
    def run(self, n_iter):
        pass

    @abstractmethod
    def get_result(self):
        pass


class Celer(Solver):
    name = 'Celer'

    def __init__(self, X, y, lmbd):
        super().__init__(X, y, lmbd)
        from celer import Lasso
        n_samples = X.shape[0]
        self.lasso = Lasso(
            alpha=self.lmbd/n_samples, max_iter=1, gap_freq=10,
            max_epochs=100000, p0=10, verbose=False, tol=1e-12, prune=0,
            fit_intercept=False, normalize=False, warm_start=False,
            positive=False
        )

    def run(self, n_iter):
        self.lasso.max_iter = n_iter
        self.lasso.fit(self.X, self.y)

    def get_result(self):
        return self.lasso.coef_


class Lasso(Solver):
    name = 'Lasso'

    def __init__(self, X, y, lmbd):
        super().__init__(X, y, lmbd)
        self.L = np.linalg.norm(X.dot(X.T), ord=2)

    def run(self, n_iter):
        n_features = self.X.shape[1]
        z_hat = np.zeros(n_features)
        for i in range(n_iter):
            grad = self.X.T.dot(self.X.dot(z_hat) - self.y)
            z_hat -= 1 / self.L * grad
            z_hat = self.st(z_hat, 1 / self.L * self.lmbd)
        self.z_hat = z_hat

    def st(self, z, mu):
        return np.sign(z) * np.maximum(0, abs(z) - mu)

    def get_result(self):
        return self.z_hat


class SkLasso(Solver):
    name = 'sklearn'

    def __init__(self, X, y, lmbd):
        from sklearn.linear_model import Lasso
        super().__init__(X, y, lmbd)
        n_samples = X.shape[0]
        self.clf = Lasso(alpha=lmbd/n_samples, fit_intercept=False, tol=0)

    def run(self, n_iter):
        self.clf.max_iter = n_iter
        self.clf.fit(self.X, self.y)

    def get_result(self):
        return self.clf.coef_
# class Liblinear(Solver):
#     name = 'Liblinear'
#
#     def __init__(self, X, y, lmbd):
#         super().__init__(X, y, lmbd)
#
#     def run(self, n_iter):
#         from sklearn.svm.liblinear import train_wrap
#         train_wrap(self.X, self.y, is_sparse=False,
#
#     def get_result(self):
#         pass


def benchmark():
    X, y = get_data(100, 50000)
    lmbd_max = abs(X.T.dot(y)).max()

    res = []
    for method in [Lasso, Celer, SkLasso]:
        res.extend(run_one_method(method, 1000, X, y, .1 * lmbd_max))

    import pandas as pd
    import matplotlib.pyplot as plt
    df = pd.DataFrame(res)
    for m in ['Celer', 'Lasso', 'sklearn']:
        df_ = df[df.method == m]
        plt.loglog(df_.time, df_.p0, label=m)
    plt.legend()
    plt.show()
