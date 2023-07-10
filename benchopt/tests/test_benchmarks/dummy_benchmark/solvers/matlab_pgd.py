from pathlib import Path
from benchopt import safe_import_context

from benchopt.helpers.matlab import MatlabSolver
from benchopt.helpers.matlab import matlab_engine, assert_matlab_installed

with safe_import_context() as import_ctx:
    import numpy as np
    assert_matlab_installed()


# File containing the function to be called from julia
MATLAB_SOLVER_FILE = str(Path(__file__).with_suffix('.m'))


class Solver(MatlabSolver):

    # Config of the solver
    name = 'Matlab-PGD'
    sampling_strategy = 'iteration'

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd


    def run(self, n_iter):
        with matlab_engine([str(Path(__file__).parent)]) as eng:
            self.beta = eng.matlab_pgd(self.X, self.y, self.lmbd, n_iter, nargout=1)


    def get_result(self):
        return np.array(self.beta).ravel()
