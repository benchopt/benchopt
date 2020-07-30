import numpy as np
import pandas as pd
from benchopt.base import CommandLineSolver
from benchopt.util import safe_import_context, import_shell_cmd
from scipy.io import savemat, loadmat

with safe_import_context() as import_ctx:
    import h5py
    train_cmd = import_shell_cmd('julia')


class Solver(CommandLineSolver):
    name = 'JuliaPGD'
    sampling_strategy = 'iteration'

    install_cmd = 'conda'
    requirements = ['julia', 'h5py']

    def set_objective(self, X, y, lmbd):

        # The regularization parameter is passed directly to the command line
        # so we store it for latter.
        self.lmbd = lmbd

        # Dump the large arrays to a file and store its name
        n_samples = X.shape[0]

        savemat(self.data_filename, {'X': X, 'y': y})

    def run(self, n_iter):
        train_cmd(f"benchmarks/lasso/solvers/lasso_pgd.jl {self.lmbd} "
                  f"{n_iter} {self.data_filename} "
                  f"{self.model_filename}")

    def get_result(self):
        data = h5py.File(self.model_filename, 'r')
        return np.array(data['/w']).ravel()
