import pytest
import tempfile

from benchopt.cli.main import run
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


def test_objective_no_cv(no_debug_log):

    no_cv = """from benchopt import BaseObjective

        class Objective(BaseObjective):
            name = "cross_val"
            min_benchopt_version = "0.0.0"

            def set_data(self, X, y): self.X, self.y = X, y
            def get_one_result(self): return 0
            def evaluate_result(self, beta): return dict(value=1)

            def get_objective(self):
                x = self.get_split(self.X, self.y)
                return dict(X=X_train, y=y_train, lmbd=1)
    """

    msg = "To use `Objective.get_split`, Objective must define a cv"
    with temp_benchmark(objective=no_cv) as benchmark:
        with pytest.raises(ValueError, match=msg):
            run([str(benchmark.benchmark_dir),
                 *'-s python-pgd -d test-dataset -n 1 -r 1 --no-plot'.split()],
                standalone_mode=False)


def test_objective_save_final_results(no_debug_log):
    save_final = """
    from benchopt import BaseObjective

    class Objective(BaseObjective):
        name = "cross_val"

        min_benchopt_version = "0.0.0"

        def set_data(self, X, y): self.X, self.y = X, y
        def get_one_result(self): return 0
        def evaluate_result(self, beta): return dict(value=1)

        def save_final_results(self, beta):
            return "test_value"

        def get_objective(self):
            return dict(X=self.X, y=self.y, lmbd=1)

    """

    import pandas as pd
    import pickle

    with temp_benchmark(objective=save_final) as benchmark:
        with CaptureRunOutput(delete_result_files=False) as out:
            run([
                str(benchmark.benchmark_dir),
                *('-s python-pgd -d test-dataset -n 1 -r 1 --no-plot').split()
            ],  standalone_mode=False)
        data = pd.read_parquet(out.result_files[0])
        with open(data.loc[0, "final_results"], "rb") as final_result_file:
            final_results = pickle.load(final_result_file)
    assert final_results == "test_value"


def test_objective_cv_splitter(no_debug_log):

    objective = """from benchopt import BaseObjective, safe_import_context
        with safe_import_context() as import_ctx:
            import numpy as np

        class Splitter():
            def split(self, X, y, groups=None):
                for i in range(len(np.unique(groups))):
                    print(f"RUN#{i}")
                    mask = groups == i
                    yield mask, ~mask

            def get_n_splits(self, groups): return len(np.unique(groups))

        class Objective(BaseObjective):
            name = "cross_val"
            min_benchopt_version = "0.0.0"

            def set_data(self, X, y):
                self.X, self.y = X, y
                self.cv_metadata = dict(groups=np.r_[
                    np.zeros(33), np.ones(33), 2 * np.ones(34)
                ])
                self.cv = Splitter()

            def get_objective(self):
                X_train, X_test, y_train, y_test = self.get_split(
                    self.X, self.y
                )
                return dict(X_train=X_train, y_train=y_train)

            def get_one_result(self): return dict(beta=0)
            def evaluate_result(self, beta): return dict(value=1)
    """

    solver = """from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = "test-solver"
        sampling_strategy = 'run_once'
        def set_objective(self, X_train, y_train): pass
        def run(self, n_iter): print("OK")
        def get_result(self): return dict(beta=1)
    """

    with temp_benchmark(objective=objective, solvers=[solver]) as benchmark:
        with CaptureRunOutput() as out:
            run([str(benchmark.benchmark_dir),
                *('-s test-solver -d test-dataset --no-plot').split()],
                standalone_mode=False)

    # test-solver appears one time as it is only run once.
    out.check_output("test-solver", repetition=1)
    out.check_output("RUN#0", repetition=1)
    out.check_output("RUN#1", repetition=1)
    out.check_output("RUN#2", repetition=1)
    out.check_output("RUN#3", repetition=0)
    out.check_output("OK", repetition=3)

    # Make sure that `-r` is enforced when specified
    with temp_benchmark(objective=objective, solvers=[solver]) as benchmark:
        with CaptureRunOutput() as out:
            run([str(benchmark.benchmark_dir),
                *('-s test-solver -d test-dataset -r 2 --no-plot').split()],
                standalone_mode=False)

    # test-solver appears one time as it is only run once.
    out.check_output("test-solver", repetition=1)
    out.check_output("RUN#0", repetition=1)
    out.check_output("RUN#1", repetition=1)
    out.check_output("RUN#2", repetition=0)
    out.check_output("RUN#3", repetition=0)
    out.check_output("OK", repetition=2)

    with temp_benchmark(objective=objective, solvers=[solver]) as benchmark:
        with CaptureRunOutput() as out:
            run([str(benchmark.benchmark_dir),
                *('-s test-solver -d test-dataset -r 5 --no-plot').split()],
                standalone_mode=False)

    # test-solver appears one time as it is only run once.
    out.check_output("test-solver", repetition=1)
    out.check_output("RUN#0", repetition=2)
    out.check_output("RUN#1", repetition=2)
    out.check_output("RUN#2", repetition=1)
    out.check_output("RUN#3", repetition=0)
    out.check_output("OK", repetition=5)

    # Make sure running in parallel does not mess up the splits
    with temp_benchmark(objective=objective, solvers=[solver]) as benchmark:
        with CaptureRunOutput() as out:
            run([
                str(benchmark.benchmark_dir),
                *('-s test-solver -d test-dataset -j 3 -r 4 --no-plot').split()
            ], standalone_mode=False)

    # test-solver appears one time as it is only run once.
    out.check_output("test-solver", repetition=1)
    out.check_output("RUN#0", repetition=2)
    out.check_output("RUN#1", repetition=1)
    out.check_output("RUN#2", repetition=1)
    out.check_output("RUN#3", repetition=0)
    out.check_output("OK", repetition=4)


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


@pytest.mark.parametrize("test_case", ["without_data_home", "with_data_home"])
def test_paths_config_key(test_case):
    if test_case == "without_data_home":
        config = """
            data_paths:
                data: /path/to/data
        """
    elif test_case == "with_data_home":
        config = """
            data_home: /path/to/home_data
            data_paths:
                data: path/to/data
        """
    else:
        raise Exception("Invalid test case value")

    custom_dataset = """
        from benchopt import BaseDataset
        from benchopt import config
        import numpy as np

        class Dataset(BaseDataset):
            name = "custom_dataset"
            def get_data(self):
                path = config.get_data_path(key="data")
                print(f"PATH${path}")

                return dict(X=np.random.rand(3, 2), y=np.ones((3,)))
    """

    with temp_benchmark(datasets=[custom_dataset], config=config) as benchmark:
        with CaptureRunOutput() as out:
            run([
                str(benchmark.benchmark_dir),
                *'-s solver-test -d custom_dataset'
                 ' -n 0 -r 1 --no-plot '
                '-o dummy*[reg=0.5]'.split()
            ], standalone_mode=False)

        if test_case == "without_data_home":
            out.check_output(r"path/to/data", repetition=1)
        elif test_case == "with_data_home":
            out.check_output(
                r"/path/to/home_data/path/to/data",
                repetition=1
            )
        else:
            raise Exception("Invalid test case value")
