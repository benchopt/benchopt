import pytest

from benchopt.cli.main import run
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.stopping_criterion import SAMPLING_STRATEGIES
from benchopt.utils.dynamic_modules import _load_class_from_module

from benchopt.tests.utils import CaptureCmdOutput


def test_solver_template():
    solvers = {"template_solver.py": "raise ImportError()"}

    with temp_benchmark(solvers=solvers) as bench:
        # Make sure that importing template_solver raises an error.
        with pytest.raises(ValueError):
            template_solver = (
                bench.benchmark_dir / 'solvers' / 'template_solver.py'
            )
            template = _load_class_from_module(
                bench.benchmark_dir, template_solver, 'Solver'
            )
            template.is_installed(raise_on_not_installed=True)

        # Make sure that this error is not raised when listing
        # all solvers from the benchmark.
        solvers = bench.get_solvers()
        assert len(solvers) == 1
        assert solvers[0].name == 'test-solver'


def test_custom_parameters(no_debug_log):
    solver = """from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = 'test-solver'
        parameters = {'param1': [0], 'param2': [9]}
        def set_objective(self, X, y, lmbd): pass
        def run(self, n_iter): pass
        def get_result(self): return dict(beta=None)
    """

    select_solvers = 'test-solver[param1=[1,2],param2=9]'

    with temp_benchmark(solvers=solver) as bench, CaptureCmdOutput() as out:
        run(
            f"{bench.benchmark_dir} -d simulated -s {select_solvers} -n 0 "
            "--no-plot".split(),
            'benchopt', standalone_mode=False)

    out.check_output(r'test-solver\[param1=0', repetition=0)
    out.check_output(r'test-solver\[param1=1,param2=9\]', repetition=2)
    out.check_output(r'test-solver\[param1=2,param2=9\]', repetition=2)


def test_solver_warm_up():

    solver1 = """from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = 'solver1'
        sampling_strategy = 'iteration'

        def set_objective(self, X, y, lmbd): pass
        def run(self, n_iter): pass
        def get_result(self): return dict(beta=None)

        def warm_up(self):
            print("WARMUP")
            self.run_once(1)
    """

    with temp_benchmark(solvers=[solver1]) as benchmark:
        with CaptureCmdOutput() as out:
            run([
                str(benchmark.benchmark_dir),
                *'-s solver1 -d test-dataset -n 0 -r 5 --no-plot'.split(),
            ], standalone_mode=False)

        # Make sure warmup is called exactly once
        out.check_output("WARMUP", repetition=1)


def test_solver_pre_run_hook():

    solver1 = """from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = 'solver1'
        sampling_strategy = 'iteration'

        def set_objective(self, X, y, lmbd): pass
        def get_result(self): return dict(beta=None)

        def pre_run_hook(self, n_iter):
            self._pre_run_hook_n_iter = n_iter
            print(f"PRERUN {n_iter}")
        def run(self, n_iter):
            assert self._pre_run_hook_n_iter == n_iter
    """

    with temp_benchmark(solvers=[solver1]) as benchmark:
        with CaptureCmdOutput() as out:
            run([
                str(benchmark.benchmark_dir),
                *'-s solver1 -d test-dataset -n 2 -r 2 --no-plot'.split()
            ], standalone_mode=False)
        out.check_output("PRERUN 2", repetition=2)


@pytest.mark.parametrize('strategy', SAMPLING_STRATEGIES)
def test_solver_invalid_get_result(strategy):

    solver = f"""from benchopt import BaseSolver

        class Solver(BaseSolver):
            name = 'solver1'
            sampling_strategy = '{strategy}'
            def set_objective(self, X, y, lmbd): pass
            def run(self, n_iter_or_cb):
                if callable(n_iter_or_cb):
                    while n_iter_or_cb():
                        pass
            def get_result(self): return 0
    """

    with temp_benchmark(solvers=solver) as benchmark:
        with pytest.raises(TypeError, match='get_result` should be a dict '):
            with CaptureCmdOutput():
                run([
                    str(benchmark.benchmark_dir),
                    *'-s solver1 -d test-dataset -n 0 -r 5 --no-plot'.split()
                ], standalone_mode=False)


@pytest.mark.parametrize('eval_every', [1, 10])
def test_solver_return_early_callback(eval_every):

    solver = f"""from benchopt import BaseSolver
    from benchopt.stopping_criterion import NoCriterion

    class Solver(BaseSolver):
        name = 'test-solver'
        sampling_strategy = 'callback'
        stopping_criterion = NoCriterion()
        def get_next(self, stop_val): return stop_val + {eval_every}
        def set_objective(self, X, y, lmbd): pass
        def run(self, cb):
            for i in range(3):
                self.val = i
                cb()
        def get_result(self): return {{'val': self.val}}
    """
    objective = """from benchopt import BaseObjective
    class Objective(BaseObjective):
        name = "test-objective"
        def set_data(self, X, y): pass
        def evaluate_result(self, val):
            print(f"EVAL#{val}")
            return 1
        def get_one_result(self): pass
        def get_objective(self): return dict(X=None, y=None, lmbd=None)
    """

    with temp_benchmark(solvers=solver, objective=objective) as bench:
        with CaptureCmdOutput() as out:
            run(
                f"{bench.benchmark_dir} -d test-dataset -n 10 "
                "--no-plot".split(),
                "benchopt", standalone_mode=False
            )
        # Make sure the solver returns early and the last value is only logged
        # once.
        out.check_output("EVAL#0", repetition=1)
        out.check_output("EVAL#2", repetition=1)
        out.check_output("EVAL#3", repetition=0)
