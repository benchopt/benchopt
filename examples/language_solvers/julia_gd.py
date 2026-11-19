from pathlib import Path

from benchopt.helpers.julia import JuliaSolver
from benchopt.helpers.julia import get_jl_interpreter


JULIA_SOLVER_FILE = str(Path(__file__).with_suffix('.jl'))


class Solver(JuliaSolver):
    name = "Julia-GD"
    sampling_strategy = "iteration"
    parameters = {"lr": [1e-3, 1e-2]}
    requirements = [
        "https://repo.prefix.dev/julia-forge::julia",
        "pip::julia",
    ]

    def set_objective(self, X):
        self.X = X
        jl = get_jl_interpreter()
        self.julia_gd = jl.include(JULIA_SOLVER_FILE)

    def warm_up(self):
        # Make sure we don't account for the Julia loading time in the
        # first iteration of the benchmark.
        self.julia_gd(self.X, self.lr, 20)

    def run(self, n_iter):
        # Here we cannot call a python callback, so we call iteratively
        # the solver with a growing number of iterations.
        self.X_hat = self.julia_gd(self.X, self.lr, n_iter)

    def get_result(self):
        return dict(X_hat=self.X_hat)
