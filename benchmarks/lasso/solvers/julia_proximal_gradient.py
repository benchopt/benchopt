from pathlib import Path
from benchopt.base import BaseSolver
from benchopt.util import safe_import_context

with safe_import_context() as import_ctx:
    from benchopt.utils.julia_helpers import get_jl_interpreter


# File containing the function to be called from julia
JULIA_SOLVER_FILE = str(Path(__file__).with_suffix('.jl'))


class Solver(BaseSolver):

    # Config of the solver
    name = 'Julia-PGD'
    stop_strategy = 'iteration'
    support_sparse = False

    # Requirements
    install_cmd = 'conda'
    requirements = ['julia', 'pip:julia']

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd

        jl = get_jl_interpreter()
        self.solve_lasso = jl.include(JULIA_SOLVER_FILE)

    def run(self, n_iter):
        self.beta = self.solve_lasso(self.X, self.y, self.lmbd, n_iter)

    def get_result(self):
        return self.beta.ravel()
