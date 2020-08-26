from benchopt.base import BaseSolver
from benchopt.util import safe_import_context

with safe_import_context() as import_ctx:
    import julia
    julia.install()
    # configure the julia runtime
    jl = julia.Julia(
        compiled_modules=False
    )


class Solver(BaseSolver):

    # Config of the solver
    name = 'JuliaPGD'
    sampling_strategy = 'iteration'
    support_sparse = False

    # Requirements
    install_cmd = 'conda'
    requirements = ['julia', 'pip:julia']

    def set_objective(self, X, y, lmbd):
        self.X, self.y, self.lmbd = X, y, lmbd

        self.solve_lasso = jl.include("benchmarks/lasso/solvers/lasso_pgd.jl")

    def run(self, n_iter):
        self.beta = self.solve_lasso(self.X, self.y, self.lmbd, n_iter)

    def get_result(self):
        return self.beta.ravel()
