from pathlib import Path

from benchopt.helpers.julia import JuliaSolver
from benchopt.helpers.julia import get_jl_interpreter
from benchopt.helpers.julia import assert_julia_installed


# File containing the function to be called from julia
JULIA_SOLVER_FILE = str(Path(__file__).with_suffix('.jl'))

# Necessary check to make it possible to install the solver
# in a conda environment without julia installed.
assert_julia_installed()


class Solver(JuliaSolver):

    # Config of the solver
    name = 'Julia-PGD'
    sampling_strategy = 'iteration'
    requirements = [
        'https://repo.prefix.dev/julia-forge::julia', 'pip::julia'
    ]

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd

        jl = get_jl_interpreter()
        self.solve_lasso = jl.include(JULIA_SOLVER_FILE)

    def run(self, n_iter):
        self.beta = self.solve_lasso(self.X, self.y, self.lmbd, n_iter)

    def get_result(self):
        return {'beta': self.beta.ravel()}
