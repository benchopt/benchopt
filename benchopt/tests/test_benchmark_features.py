import pytest

from benchopt.cli.main import run
from benchopt.utils.dynamic_modules import _load_class_from_module

from benchopt.tests import SELECT_ONE_PGD
from benchopt.tests import SELECT_ONE_SIMULATED
from benchopt.tests import SELECT_ONE_OBJECTIVE
from benchopt.tests import DUMMY_BENCHMARK
from benchopt.tests import DUMMY_BENCHMARK_PATH
from benchopt.tests.utils import patch_import
from benchopt.tests.utils import patch_benchmark
from benchopt.tests.utils import CaptureRunOutput

from benchopt.utils.temp_benchmark import temp_benchmark


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


def test_objective_cv():

    pytest.importorskip('sklearn')

    objective = """from benchopt import BaseObjective, safe_import_context

        with safe_import_context() as import_ctx:
            import numpy as np
            from sklearn.model_selection import KFold


        class Objective(BaseObjective):

            name = "failing"
            min_benchopt_version = "0.0.0"

            def set_data(self, X, y):
                self.X, self.y = X, y
                self.cv = KFold(3)

            def get_one_solution(self):
                return np.zeros(self.X.shape[1])

            def compute(self, beta):
                return dict(value=1)

            def get_objective(self):
                X_train, X_test, y_train, y_test = self.get_split(
                    self.X, self.y
                )
                return dict(X=X_train, y=y_train, lmbd=1)
    """

    failing_objective = objective.replace("self.cv = KFold(3)", "")
    with temp_benchmark(objective=failing_objective) as benchmark:
        with pytest.raises(
                ValueError, match="To use get_split, you need to define a cv"
        ):
            run([str(benchmark.benchmark_dir),
                 *'-s python-pgd -d test-dataset -n 1 -r 1 --no-plot'.split()],
                standalone_mode=False)

    with temp_benchmark(objective=objective) as benchmark:
        with CaptureRunOutput() as out:
            run([str(benchmark.benchmark_dir),
                 *('-s Python-PGD[step_size=1] -d test-dataset '
                   '-n 1 -r 1 --no-plot').split()],
                standalone_mode=False)

        out.check_output("Python-PGD", repetition=3)
