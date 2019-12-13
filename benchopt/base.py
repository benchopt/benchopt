import time
import numpy as np
import pandas as pd
from abc import abstractmethod
import matplotlib.pyplot as plt
from collections import namedtuple
from importlib import import_module


Cost = namedtuple('Cost', 'data method n_iter time loss'.split(' '))


class Solver(object):
    name = 'solver'

    def __init__(self, **parameters):
        pass

    @abstractmethod
    def set_loss(self, X, y, lmbd):
        '''Prepare the data'''
        pass

    @abstractmethod
    def run(self, n_iter):
        pass

    @abstractmethod
    def get_result(self):
        pass


def run_one_method(data_name, method_class, score, loss, parameters, max_iter):
    method = method_class(*parameters)
    method.set_loss(*loss)
    res = []
    list_iter = np.unique(np.logspace(0, np.log10(max_iter), 20, dtype=int))
    for n_iter in list_iter:
        print(f"{n_iter} / {max_iter}\r", end='', flush=True)
        t_start = time.time()
        method.run(n_iter=n_iter)
        delta_t = time.time() - t_start
        beta_hat_i = method.get_result()
        loss_value = score(*loss, beta_hat_i)
        res.append(Cost(data=data_name, method=method.name, n_iter=n_iter,
                        time=delta_t, loss=loss_value))
    return res


def run_benchmark(bench_name, max_iter=1000):

    module = import_module(bench_name)
    datasets = module.datasets
    solvers = module.solvers
    score = module.score_result

    res = []
    for data_name, (get_data, args) in datasets.items():
        loss = get_data(**args)
        for solver in solvers:
            parameters = {}
            res.extend(run_one_method(data_name, solver, score, loss,
                                      parameters, max_iter))
    df = pd.DataFrame(res)
    plot_benchmark(df)


def plot_benchmark(df):
    datasets = df.data.unique()
    methods = df.method.unique()
    for data in datasets:
        plt.figure(data)
        df_data = df[df.data == data]
        for m in methods:
            df_ = df_data[df_data.method == m]
            plt.loglog(df_.time, df_.loss, label=m)
        plt.legend()
    plt.show()
