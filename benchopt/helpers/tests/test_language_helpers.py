import sys
import pytest

from benchopt.cli.main import install, run
from benchopt.utils.temp_benchmark import temp_benchmark

from benchopt.tests.utils import CaptureCmdOutput


DATASET = """from benchopt import BaseDataset
import numpy as np

class Dataset(BaseDataset):
    name = 'simulated'
    def get_data(self): return dict(X=np.random.randn(10, 2))
"""

OBJECTIVE = """from benchopt import BaseObjective

class Objective(BaseObjective):
    name = 'test'

    def set_data(self, X): self.X = X
    def get_objective(self): return dict(X=self.X)
    def evaluate_result(self, beta): return dict(value=1)
    def get_one_result(self): return dict(beta=1)
"""


def test_r_solver(test_env_name, no_debug_log):
    solver = """
    from benchopt import BaseSolver
    from benchopt.helpers.r_lang import import_func_from_r_file, converter_ctx

    import numpy as np

    from pathlib import Path
    R_FILE = str(Path(__file__).with_suffix('.R'))

    class Solver(BaseSolver):
        name = 'r_solver'
        requirements = ['r-base', 'rpy2']

        def set_objective(self, X):
            self.X= X

            robjects = import_func_from_r_file(R_FILE)
            self.run_r = robjects.r['run_r']

        def run(self, n_iter):
            with converter_ctx():
                self.beta = np.asarray(self.run_r(self.X, n_iter))

        def get_result(self): return {'beta': self.beta.ravel()}
    """
    r_solver = """##' @export

    run_r <- function(X, n_iter){
        p <- ncol(X)
        parameters <- numeric(p)
        return(parameters)
    }
    """

    with temp_benchmark(
        objective=OBJECTIVE,
        datasets=DATASET,
        solvers={"r_solver.py": solver, "r_solver.R": r_solver}
    ) as bench:
        with CaptureCmdOutput() as out:
            install(
                [str(bench.benchmark_dir), '--env-name', test_env_name],
                'benchopt', standalone_mode=False
            )
        out.check_output("r_solver:", repetition=1)
        solver = bench.get_solvers()[0]
        solver.is_installed(
            env_name=test_env_name, raise_on_not_installed=True
        )
        with CaptureCmdOutput() as out:
            run([
                str(bench.benchmark_dir), '-s', 'r_solver', '-n', '1', '-r', 1,
                '-d', 'simulated', '--no-plot', '--env-name', test_env_name
            ], 'benchopt', standalone_mode=False)

        out.check_output("r_solver:", repetition=3)


@pytest.mark.timeout(300)
def test_julia_solver(test_env_name, no_debug_log):
    if sys.platform.startswith("win"):
        pytest.skip("Julia's PyCall library fail to install on Windows")

    solver = """
    from benchopt.helpers.julia import JuliaSolver
    from benchopt.helpers.julia import get_jl_interpreter

    from pathlib import Path
    JULIA_SOLVER_FILE = str(Path(__file__).with_suffix('.jl'))

    class Solver(JuliaSolver):
        name = 'julia_solver'
        requirements = [
            'https://repo.prefix.dev/julia-forge::julia', 'pip::julia'
        ]

        def set_objective(self, X):
            self.X= X

            jl = get_jl_interpreter()
            self.run_julia = jl.include(JULIA_SOLVER_FILE)

        def run(self, n_iter): self.beta = self.run_julia(self.X, n_iter)
        def get_result(self): return {'beta': self.beta.ravel()}
    """
    julia_solver = """using Core
    using LinearAlgebra

    function run_julia(X, n_iter)
        n, p = size(X)
        beta = zeros(p)
        return beta
    end
    """

    with temp_benchmark(
        objective=OBJECTIVE,
        datasets=DATASET,
        solvers={"julia.py": solver, "julia.jl": julia_solver},
    ) as bench:

        with CaptureCmdOutput() as out:
            install(
                [str(bench.benchmark_dir), '--env-name', test_env_name],
                'benchopt', standalone_mode=False
            )
        out.check_output("julia_solver:", repetition=1)
        solver = bench.get_solvers()[0]
        solver.is_installed(
            env_name=test_env_name, raise_on_not_installed=True
        )

        with CaptureCmdOutput() as out:
            run([
                str(bench.benchmark_dir), '-s', 'julia_solver', '-n', '1',
                '-r', 1, '-d', 'simulated', '--no-plot',
                '--env-name', test_env_name
            ], 'benchopt', standalone_mode=False)

        out.check_output("julia_solver:", repetition=3)
