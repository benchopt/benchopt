import pytest
import tempfile
import warnings

import benchopt
from benchopt.cli.main import run
from benchopt.cli.main import test as _cmd_test
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.utils.dynamic_modules import _load_class_from_module

from benchopt.tests import SELECT_ONE_PGD
from benchopt.tests import SELECT_ONE_SIMULATED
from benchopt.tests import SELECT_ONE_OBJECTIVE
from benchopt.tests import DUMMY_BENCHMARK
from benchopt.tests import DUMMY_BENCHMARK_PATH
from benchopt.tests.utils import patch_import
from benchopt.tests.utils import patch_benchmark
from benchopt.tests.utils import CaptureRunOutput


def test_template_dataset():
    # Make sure that importing template_dataset raises an error.
    with pytest.raises(ImportError):
        template_dataset = (
            DUMMY_BENCHMARK_PATH / 'datasets' / 'template_dataset.py'
        )
        _load_class_from_module(
            template_dataset, 'Dataset', DUMMY_BENCHMARK_PATH
        )

    # Make sure that this error is not raised when listing all datasets from
    # the benchmark.
    DUMMY_BENCHMARK.get_datasets()


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


def test_benchmark_submodule():
    with pytest.raises(ValueError, match="raises an error"):
        run([
            str(DUMMY_BENCHMARK_PATH), '-s', 'solver-test[raise_error=True]',
            '-d', SELECT_ONE_SIMULATED
        ], 'benchopt', standalone_mode=False)


def test_benchopt_min_version():
    with patch_benchmark(DUMMY_BENCHMARK, component="objective",
                         min_benchopt_version="99.0"):
        with pytest.raises(RuntimeError, match="pip install -U"):
            run([str(DUMMY_BENCHMARK_PATH)], 'benchopt',
                standalone_mode=False)

    with CaptureRunOutput() as out:
        # check than benchmark with low requirement runs
        run([
            str(DUMMY_BENCHMARK_PATH), '-l', '-d', SELECT_ONE_SIMULATED,
            '-f', SELECT_ONE_PGD, '-n', '1', '-r', '1', '-o',
            SELECT_ONE_OBJECTIVE, '--no-plot'
        ], 'benchopt', standalone_mode=False)

    out.check_output('Simulated', repetition=1)


@pytest.mark.parametrize('error', [ImportError, ValueError])
@pytest.mark.parametrize('raise_install_error', [0, 1])
def test_error_reporting(error, raise_install_error):

    expected_exc = (
        ImportError if raise_install_error and error is ImportError
        else SystemExit
    )

    import os
    prev_value = os.environ.get('BENCHOPT_RAISE_INSTALL_ERROR', '0')

    def raise_error():
        raise error("important debug message")

    try:
        os.environ['BENCHOPT_RAISE_INSTALL_ERROR'] = str(raise_install_error)
        with patch_import(dummy_solver_import=raise_error):
            with CaptureRunOutput() as out, pytest.raises(expected_exc):
                run([
                    str(DUMMY_BENCHMARK_PATH), '-s', "solver-test",
                    '-d', SELECT_ONE_SIMULATED, '-n', '1', '--no-plot'
                ], 'benchopt', standalone_mode=False)

        if not raise_install_error:
            out.check_output(
                f"{error.__name__}: important debug message", repetition=1
            )
    finally:
        os.environ['BENCHOPT_RAISE_INSTALL_ERROR'] = prev_value


def test_ignore_hidden_files():
    # Non-regression test to make sure hidden files in datasets and solvers
    # are ignored. If this is not the case, the call to run will fail if it
    # is not ignored as there is no Dataset/Solver defined in the file.
    with tempfile.NamedTemporaryFile(
        dir=str(DUMMY_BENCHMARK_PATH / 'datasets'),
        prefix='.hidden_dataset_',
        suffix='.py',
        delete=True
    ), CaptureRunOutput():
        run([
            str(DUMMY_BENCHMARK_PATH), '-l', '-d',
            SELECT_ONE_SIMULATED, '-f', SELECT_ONE_PGD, '-n', '1',
            '-r', '1', '-o', SELECT_ONE_OBJECTIVE, '--no-plot'
        ], 'benchopt', standalone_mode=False)

    with tempfile.NamedTemporaryFile(
        dir=str(DUMMY_BENCHMARK_PATH / 'solvers'),
        prefix='.hidden_solver_',
        suffix='.py',
        delete=True
    ), CaptureRunOutput():
        run([
            str(DUMMY_BENCHMARK_PATH), '-l', '-d',
            SELECT_ONE_SIMULATED, '-f', SELECT_ONE_PGD, '-n', '1',
            '-r', '1', '-o', SELECT_ONE_OBJECTIVE, '--no-plot'
        ], 'benchopt', standalone_mode=False)


@pytest.mark.parametrize("n_iter", [1, 2, 5])
def test_run_once_iteration(n_iter):

    solver1 = f"""from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = 'solver1'
        sampling_strategy = 'iteration'

        def set_objective(self, X, y, lmbd):
            self.n_features = X.shape[1]
            self.run_once({n_iter})

        def run(self, n_iter): print(f"RUNONCE({{n_iter}})")

        def get_result(self, **data):
            return {{'beta': np.zeros(self.n_features)}}
    """

    with temp_benchmark(solvers=[solver1]) as benchmark:
        with CaptureRunOutput() as out:
            run([
                str(benchmark.benchmark_dir),
                *'-s solver1 -d test-dataset -n 0 -r 1 --no-plot'.split(),
                *'-o dummy*[reg=0.5]'.split()
            ], standalone_mode=False)
        out.check_output(rf"RUNONCE\({n_iter}\)", repetition=1)


@pytest.mark.parametrize("n_iter", [1, 2, 5])
def test_run_once_callback(n_iter):

    solver1 = f"""from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = 'solver1'
        sampling_strategy = 'callback'

        def set_objective(self, X, y, lmbd):
            self.n_features = X.shape[1]
            self.run_once({n_iter})

        def run(self, cb):
            i = 0
            while cb():
                i += 1
            print(f"RUNONCE({{i}})")

        def get_result(self, **data):
            return {{'beta': np.zeros(self.n_features)}}
    """

    with temp_benchmark(solvers=[solver1]) as benchmark:
        with CaptureRunOutput() as out:
            run([
                str(benchmark.benchmark_dir),
                *'-s solver1 -d test-dataset -n 0 -r 1 --no-plot'.split(),
                *'-o dummy*[reg=0.5]'.split()
            ], standalone_mode=False)

        out.check_output(rf"RUNONCE\({n_iter}\)", repetition=1)


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

        def get_result(self, **data):
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


##############################################################################
# Test for deprecated features in 1.5
##############################################################################


def test_deprecated_stopping_strategy():
    # XXX remove in 1.5
    assert benchopt.__version__ < '1.5'

    solver1 = """from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = 'solver1'
        stopping_strategy = 'iteration'

        def run(self, n_iter): pass

        def set_objective(self, X, y, lmbd):
            self.n_features = X.shape[1]

        def get_result(self, **data):
            return {'beta': np.zeros(self.n_features)}
    """

    solver2 = solver1.replace("stopping_strategy", "sampling_strategy")
    solver2 = solver2.replace("solver1", "solver2")

    with temp_benchmark(solvers=[solver1, solver2]) as benchmark:
        with pytest.warns(
                FutureWarning,
                match="'stopping_strategy' attribute is deprecated"):
            run([str(benchmark.benchmark_dir),
                 *'-s solver1 -d test-dataset -n 1 -r 1 --no-plot'.split()],
                standalone_mode=False)

        run([str(benchmark.benchmark_dir),
             *'-s solver2 -d test-dataset -n 1 -r 1 --no-plot'.split()],
            standalone_mode=False)


def test_deprecated_support_sparse():
    # XXX remove in 1.5
    assert benchopt.__version__ < '1.5'

    solver1 = """from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = 'solver1'
        support_sparse = True

        def run(self, n_iter): pass

        def set_objective(self, X, y, lmbd):
            self.n_features = X.shape[1]

        def get_result(self, **data):
            return dict(beta=np.zeros(self.n_features))
    """

    with temp_benchmark(solvers=solver1) as benchmark:
        with pytest.warns(
                FutureWarning,
                match="`support_sparse = False` is deprecated"):
            run([str(benchmark.benchmark_dir),
                 *'-s solver1 -d test-dataset -n 1 -r 1 --no-plot'.split()],
                standalone_mode=False)


def test_deprecated_compute():
    # XXX remove in 1.5
    assert benchopt.__version__ < '1.5'

    # Make sure that BaseObjective is compatible with compute, with both
    # get_result returning a dict or a scalar.
    objective = """from benchopt import BaseObjective

    class Objective(BaseObjective):
        name = 'dummy'

        def set_data(self, X, y):
            self.X, self.y = X, y

        def compute(self, beta):
            return 1

        def get_one_result(self):
            return dict(beta=0)

        def get_objective(self):
            return dict(X=self.X, y=self.y, lmbd=0)
    """

    match = "`Objective.compute` was renamed `Objective.evaluate_result` "
    with temp_benchmark(objective=objective) as benchmark:
        with pytest.warns(FutureWarning, match=match):
            run([str(benchmark.benchmark_dir),
                 *'-s python-pgd -d test-dataset -n 1 -r 1 --no-plot'.split()],
                standalone_mode=False)

    solver1 = """from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = 'solver1'

        def run(self, n_iter): pass

        def set_objective(self, X, y, lmbd):
            self.n_features = X.shape[1]

        def get_result(self, **data):
            return np.zeros(self.n_features)
    """
    match = r"Solver.get_result\(\) should return a dict"
    with temp_benchmark(objective=objective, solvers=solver1) as benchmark:
        with pytest.warns(FutureWarning, match=match):
            run([str(benchmark.benchmark_dir),
                 *'-s solver1 -d test-dataset -n 1 -r 1 --no-plot'.split()],
                standalone_mode=False)

    # Make sure that no warning is raised if using evaluate_result.
    objective = objective.replace("compute", "evaluate_result")
    with temp_benchmark(objective=objective) as benchmark:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            run([str(benchmark.benchmark_dir),
                 *'-s python-pgd -d test-dataset -n 1 -r 1 --no-plot'.split()],
                standalone_mode=False)


def test_deprecated_callback():
    # XXX remove in 1.5
    assert benchopt.__version__ < '1.5'

    # Make sure that BaseObjective is compatible with compute, with both
    # get_result returning a dict or a scalar.
    objective = """from benchopt import BaseObjective

    class Objective(BaseObjective):
        name = 'dummy'

        def set_data(self, X, y):
            self.X, self.y = X, y

        def compute(self, beta):
            return 1

        def get_one_result(self):
            return dict(beta=0)

        def get_objective(self):
            return dict(X=self.X, y=self.y, lmbd=0)
    """

    solver = """from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = 'solver1'
        sampling_strategy = "callback"

        def run(self, cb):
            self.beta = 0
            while cb(self.beta):
                pass

        def set_objective(self, X, y, lmbd):
            self.p = X.shape[1]

        def get_result(self, **data):
            return 0
    """
    match = r"the callback does not take any arguments."
    with temp_benchmark(objective=objective, solvers=solver) as benchmark:
        with pytest.warns(FutureWarning, match=match):
            run([str(benchmark.benchmark_dir),
                 *'-s solver1 -d test-dataset -n 1 -r 1 --no-plot'.split()],
                standalone_mode=False)

    solver1 = solver.replace("cb(self.beta)", "cb(dict(beta=self.beta))")
    with temp_benchmark(objective=objective, solvers=solver1) as benchmark:
        with pytest.warns(FutureWarning, match=match):
            run([str(benchmark.benchmark_dir),
                 *'-s solver1 -d test-dataset -n 1 -r 1 --no-plot'.split()],
                standalone_mode=False)

    solver = solver.replace("cb(self.beta)", "cb()")
    match = r"Solver.get_result\(\) should return a dict"
    with temp_benchmark(objective=objective, solvers=solver) as benchmark:
        with pytest.warns(FutureWarning, match=match):
            run([str(benchmark.benchmark_dir),
                 *'-s solver1 -d test-dataset -n 1 -r 1 --no-plot'.split()],
                standalone_mode=False)

    solver = solver.replace("return 0", "return dict(beta=0)")
    match = "`Objective.compute` was renamed `Objective.evaluate_result` "
    with temp_benchmark(objective=objective, solvers=solver) as benchmark:
        with pytest.warns(FutureWarning, match=match):
            run([str(benchmark.benchmark_dir),
                 *'-s solver1 -d test-dataset -n 1 -r 1 --no-plot'.split()],
                standalone_mode=False)

    objective = objective.replace("compute", "evaluate_result")
    with temp_benchmark(objective=objective, solvers=solver) as benchmark:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            run([str(benchmark.benchmark_dir),
                 *'-s solver1 -d test-dataset -n 1 -r 1 --no-plot'.split()],
                standalone_mode=False)


def test_deprecated_get_one_solution():
    # XXX remove in 1.5
    assert benchopt.__version__ < '1.5'

    # Make sure that BaseObjective is compatible with compute, with both
    # get_result returning a dict or a scalar.
    objective = """from benchopt import BaseObjective

    class Objective(BaseObjective):
        name = 'dummy'

        def set_data(self, X, y):
            self.X, self.y = X, y

        def evaluate_result(self, beta):
            return 1

        def get_one_solution(self):
            return dict(beta=0)

        def get_objective(self):
            return dict(X=self.X, y=self.y, lmbd=0)
    """

    match = "`Objective.get_one_solution` is renamed `Objective.get_one_result"
    with temp_benchmark(objective=objective) as benchmark:
        # with CaptureRunOutput() as out:
            with pytest.raises(SystemExit, match='False'):
                print(f'{benchmark.benchmark_dir} -- -k test_benchmark_objective')
                import ipdb; ipdb.set_trace()
                _cmd_test([str(benchmark.benchmark_dir),
                           *'-- -k test_benchmark_objective'.split()],
                          standalone_mode=False)
            out.check_output(match, repetition=1)

    objective = objective.replace("get_one_solution", "get_one_result")
    with temp_benchmark(objective=objective) as benchmark:
        with CaptureRunOutput() as out:
            with pytest.raises(SystemExit, match='False'):
                _cmd_test([str(benchmark.benchmark_dir),
                           *'-- -k test_benchmark_objective'.split()],
                          standalone_mode=False)
        out.check_output(match, repetition=0)
