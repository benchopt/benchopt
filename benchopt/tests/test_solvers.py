import pytest

from benchopt.cli.main import run
from benchopt.cli.main import test as _cmd_test
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.stopping_criterion import SAMPLING_STRATEGIES
from benchopt.utils.dynamic_modules import _load_class_from_module

from benchopt.tests import DUMMY_BENCHMARK
from benchopt.tests import DUMMY_BENCHMARK_PATH
from benchopt.tests.utils import CaptureRunOutput


def test_template_solver():
    # Make sure that importing template_dataset raises an error.
    with pytest.raises(ImportError):
        template_dataset = (
            DUMMY_BENCHMARK_PATH / 'solvers' / 'template_solver.py'
        )
        _load_class_from_module(
            template_dataset, 'Solver', DUMMY_BENCHMARK_PATH
        )

    # Make sure that this error is not raised when listing all solvers from
    # the benchmark.
    DUMMY_BENCHMARK.get_solvers()


def test_warm_up():

    solver1 = """from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = 'solver1'
        sampling_strategy = 'iteration'

        def set_objective(self, X, y, lmbd):
            self.n_features = X.shape[1]

        def warm_up(self):
            print("WARMUP")
            self.run_once(1)

        def run(self, n_iter): pass

        def get_result(self):
            return {'beta': np.zeros(self.n_features)}
    """

    with temp_benchmark(solvers=[solver1]) as benchmark:
        with CaptureRunOutput() as out:
            run([
                str(benchmark.benchmark_dir),
                *'-s solver1 -d test-dataset -n 0 -r 5 --no-plot'.split(),
                *'-o dummy*[reg=0.5]'.split()
            ], standalone_mode=False)

        # Make sure warmup is called exactly once
        out.check_output("WARMUP", repetition=1)


def test_pre_run_hook():

    solver1 = """from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = 'solver1'
        sampling_strategy = 'iteration'

        def set_objective(self, X, y, lmbd):
            self.n_features = X.shape[1]

        def pre_run_hook(self, n_iter):
            self._pre_run_hook_n_iter = n_iter

        def run(self, n_iter):
            assert self._pre_run_hook_n_iter == n_iter

        def get_result(self):
            return {'beta': np.zeros(self.n_features)}
    """

    with temp_benchmark(solvers=[solver1]) as benchmark:
        with CaptureRunOutput() as out:
            run([
                str(benchmark.benchmark_dir),
                *'-s solver1 -d test-dataset -n 0 -r 5 --no-plot '
                '-o dummy*[reg=0.5]'.split()
            ], standalone_mode=False)

        with CaptureRunOutput() as out:
            with pytest.raises(SystemExit, match="False"):
                _cmd_test([
                    str(benchmark.benchmark_dir), '-k', 'solver1',
                    '--skip-install', '-v'
                ], standalone_mode=False)

        # Make sure warmup is called exactly once
        out.check_output("3 passed, 1 skipped, 7 deselected", repetition=1)


@pytest.mark.parametrize('strategy', SAMPLING_STRATEGIES)
def test_invalid_get_result(strategy):

    solver1 = f"""from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = 'solver1'
        strategy = '{strategy}'

        def set_objective(self, X, y, lmbd): pass
        def run(self, n_iter): pass

        def get_result(self):
            return 0
    """

    with temp_benchmark(solvers=[solver1]) as benchmark:
        with pytest.raises(TypeError, match='get_result` should be a dict '):
            with CaptureRunOutput():
                run([
                    str(benchmark.benchmark_dir),
                    *'-s solver1 -d test-dataset -n 0 -r 5 --no-plot'.split(),
                    *'-o dummy*[reg=0.5]'.split()
                ], standalone_mode=False)
