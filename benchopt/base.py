import os
import venv
import time
import numpy as np
import pandas as pd
from joblib import Memory
from abc import abstractmethod
import matplotlib.pyplot as plt
from collections import namedtuple
from importlib import import_module


CACHE_DIR = '.'
VENV_DIR = './.venv/'


if not os.path.exists(VENV_DIR):
    os.mkdir(VENV_DIR)


mem = Memory(location=CACHE_DIR, verbose=0)


Cost = namedtuple('Cost', 'data method n_iter time loss'.split(' '))


class BaseSolver(object):
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


@mem.cache
def run_one_method(data_name, method_class, score, loss, parameters, max_iter):
    method = method_class(*parameters)
    method.set_loss(*loss)
    res = []
    list_iter = np.unique(np.logspace(0, np.log10(max_iter), 20, dtype=int))
    for n_iter in list_iter:
        print(f"{method.name}: {n_iter} / {max_iter}\r", end='', flush=True)
        t_start = time.time()
        method.run(n_iter=n_iter)
        delta_t = time.time() - t_start
        beta_hat_i = method.get_result()
        loss_value = score(*loss, beta_hat_i)
        res.append(Cost(data=data_name, method=method.name, n_iter=n_iter,
                        time=delta_t, loss=loss_value))
    print(f"{method.name}: done".ljust(40))
    return res


def run_benchmark(bench, max_iter=10):

    module_name = f"benchmarks.{bench}"
    module = import_module(module_name)
    score = module.score_result
    datasets = module.DATASETS

    solvers, *_ = get_solvers(bench)
    solver_classes = [import_module(f"{module_name}.{solver_name}").Solver
                      for solver_name in solvers]

    res = []
    for data_name, (get_data, args) in datasets.items():
        loss = get_data(**args)
        for solver in solver_classes:
            parameters = {}
            # if solver.name in ['Lightning']:
            #     run_one_method.call(data_name, solver, score, loss,
            #                         parameters, max_iter)
            try:
                res.extend(run_one_method(data_name, solver, score, loss,
                                          parameters, max_iter))
            except Exception:
                import traceback
                traceback.print_exc()
    df = pd.DataFrame(res)
    plot_benchmark(df)


def plot_benchmark(df):
    datasets = df.data.unique()
    methods = df.method.unique()
    for data in datasets:
        plt.figure(data)
        df_data = df[df.data == data]
        c_star = df_data.loss.min()
        for m in methods:
            df_ = df_data[df_data.method == m]
            plt.loglog(df_.time, df_.loss - c_star + 1e-7, label=m)
        plt.legend()
    plt.show()


def run_benchmark_in_venv(bench, max_iter=10):
    create_bench_env(bench)

    env_name = f"{VENV_DIR}/{bench}"
    script = f"""
        source {env_name}/bin/activate
        benchopt run --bench {bench} --max-iter {max_iter}
    """
    run_bash(script)


def create_bench_env(bench):
    solvers, pip, sh = get_solvers(bench)

    # Create a virtual env for the benchmark
    env_name = f"{VENV_DIR}/{bench}"
    if not os.path.exists(env_name):
        venv.create(env_name, with_pip=True)

    # Install the packages necessary for the benchmark's solvers with pip
    script = f"""
        source {env_name}/bin/activate
        pip install numpy cython
        pip install . {" ".join(pip)}
    """
    print(f"Installing venv for {bench}:....", end='', flush=True)
    run_bash(script)
    print("done")

    # Install the packages necessary for the benchmark's solvers with pip
    if len(sh) > 0:
        raise NotImplementedError("Cannot install packages with bash yet.")


def run_bash(script):
    with open("/tmp/script_bash_benchopt.sh", 'w') as f:
        f.write(script)

    os.system("bash /tmp/script_bash_benchopt.sh")


def get_solvers(bench):
    import yaml

    with open('solvers.yml') as f:
        all_solvers = yaml.safe_load(f)

    bench_solvers = []
    pip_install = []
    sh_install = []
    for solver, infos in all_solvers.items():
        if bench in infos['bench']:
            bench_solvers.append(solver)
            if 'pip_install' in infos:
                pip_install.append(infos['pip_install'])
            elif 'sh_install' in infos:
                sh_install.append(infos['sh_install'])

    return bench_solvers, pip_install, sh_install
