from joblib import Parallel, delayed

from benchopt.tests.utils import CaptureRunOutput
from benchopt.utils.temp_benchmark import temp_benchmark


def test_pickling_dynamic_module():
    # Make sure the dynamic modules can be pickled by joblib. In particular,
    # this is necessary for nested parallelism in distributed context.
    #
    # This test check that the module containing a solver can be pickled, and
    # that the dynamic benchmark_utils module can be retrieved in the process.

    solver = """
    from benchopt import BaseSolver
    from benchmark_utils.test1 import func1

    class Solver(BaseSolver):
        name = "test-solver"
        def set_objective(self, X, y, reg): self.X, self.y = X, y
        def run(self, _): func1()
        def get_result(self): return dict(beta=1)
    """

    with temp_benchmark(
            solvers=[solver],
            benchmark_utils={'test1': 'def func1(): print("FUNC1")'}
    ) as benchmark:
        # Get the solver from the list of tuples
        Solver, _ = benchmark.check_solver_patterns(["test-solver"])[0]
        assert Solver.is_installed()

        with CaptureRunOutput() as out:
            Solver.run(None, None)
        out.check_output("FUNC1", repetition=1)

        # This will fail if the benchmark_utils module is not pickled by value
        # by cloudpickle.
        with CaptureRunOutput():
            Parallel(n_jobs=2)(
                delayed(Solver.run)(None, None) for _ in range(2)
            )
