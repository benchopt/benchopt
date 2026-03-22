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

    parameters = {'lr': [1e-3, 1e-2]}

    def set_objective(self, X):
        self.X = X

        jl = get_jl_interpreter()
        self.gd = jl.include(JULIA_SOLVER_FILE)

    def run(self, n_iter):
        self.X_hat = self.gd(self.X, self.lr, n_iter)

    def get_result(self):
        return {'X_hat': self.X_hat}
