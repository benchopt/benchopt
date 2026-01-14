import os
import re
import pytest
from pathlib import Path

from benchopt.cli.main import run
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.utils.dynamic_modules import _load_class_from_module

from benchopt.tests.utils import patch_import
from benchopt.tests.utils import CaptureCmdOutput


def test_template_dataset():
    datasets = {"template_dataset.py": "raise ImportError()"}
    with temp_benchmark(datasets=datasets) as bench:
        # Make sure that importing template_dataset raises an error.
        with pytest.raises(ValueError):
            template_dataset = (
                bench.benchmark_dir / 'datasets' / 'template_dataset.py'
            )
            template = _load_class_from_module(
                bench.benchmark_dir, template_dataset, 'Dataset'
            )
            template.is_installed(raise_on_not_installed=True)

        # Make sure that this error is not raised when listing
        # all datasets from the benchmark.
        all_dataset = bench.get_datasets()
        assert not any(d.name == template.name for d in all_dataset)


def test_ignore_hidden_files(no_debug_log):
    # Non-regression test to make sure hidden files in datasets and solvers
    # are ignored. If this is not the case, the call to run will fail if it
    # is not ignored as there is no Dataset/Solver defined in the file.
    datasets = {".hidden_dataset_.py": ""}
    with temp_benchmark(datasets=datasets) as bench:
        with CaptureCmdOutput() as out:
            run(
                f"{bench.benchmark_dir} -d test-dataset -s test-solver "
                "-n 1 -r 1 --no-plot".split(),
                'benchopt', standalone_mode=False
            )
        out.check_output("test-dataset", repetition=1)
        out.check_output("test-solver", repetition=3)

    solvers = {".hidden_solverdataset_.py": ""}
    with temp_benchmark(solvers=solvers) as bench:
        with CaptureCmdOutput() as out:
            run(
                f"{bench.benchmark_dir} -d test-dataset -s test-solver "
                "-n 1 -r 1 --no-plot".split(),
                'benchopt', standalone_mode=False
            )
        out.check_output("test-dataset", repetition=1)
        out.check_output("test-solver", repetition=3)


def test_benchmark_submodule():
    solver = """from benchopt import BaseSolver
    from benchmark_utils.dummy_submodule.subsubmodule import error_raiser

    class Solver(BaseSolver):
        name = "test-solver"
        def set_objective(self, X, y, lmbd): pass
        def run(self, _): error_raiser()
        def get_result(): pass
    """

    utils = {
        'dummy_submodule/subsubmodule.py': """
        def error_raiser():
            raise ValueError("This function raises an error.")

        """,
    }

    with temp_benchmark(solvers=solver, benchmark_utils=utils) as bench:
        with pytest.raises(ValueError, match="raises an error"):
            run([
                str(bench.benchmark_dir),
                *"-s test-solver -d test-dataset".split()
            ], 'benchopt', standalone_mode=False)


def test_benchopt_min_version():
    objective = """from benchopt import BaseObjective

    class Objective(BaseObjective):
        name = "test"
        min_benchopt_version = "99.9"
        def set_data(self, X, y): pass
        def evaluate_result(self, beta): return 1
        def get_one_result(self): return dict(beta=1)
        def get_objective(self): return dict(X=None, y=None, lmbd=None)
    """
    run_args = "-d test-dataset -f test-solver -n 1 -r 1 --no-plot".split()

    with temp_benchmark(objective=objective) as bench:
        with pytest.raises(RuntimeError, match="pip install -U"):
            run(
                [str(bench.benchmark_dir), *run_args],
                'benchopt', standalone_mode=False
            )

    objective = objective.replace("99.9", "0.0")
    with temp_benchmark(objective=objective) as bench:
        with CaptureCmdOutput() as out:
            # check than benchmark with low requirement runs
            run(
                [str(bench.benchmark_dir), *run_args],
                'benchopt', standalone_mode=False
            )

    out.check_output('test-dataset', repetition=1)
    out.check_output('test-solver', repetition=7)


@pytest.mark.parametrize('error', [ImportError, ValueError])
@pytest.mark.parametrize('raise_install_error', [0, 1])
def test_import_error_reporting(error, raise_install_error):

    expected_exc = error if raise_install_error else SystemExit

    solver = """from benchopt import BaseSolver

    import fake_module

    class Solver(BaseSolver):
        name = "solver-test"
        def set_objective(self, X, y): pass
        def run(self, _): pass
        def get_result(self): return dict(beta=0)

    """

    def raise_error():
        raise error("important debug message")

    try:
        prev_value = os.environ.get('BENCHOPT_RAISE_INSTALL_ERROR', None)
        os.environ['BENCHOPT_RAISE_INSTALL_ERROR'] = str(raise_install_error)
        with patch_import(fake_module=raise_error):
            with temp_benchmark(solvers=solver) as bench:
                with CaptureCmdOutput() as out, pytest.raises(expected_exc):
                    run([
                        *f"{bench.benchmark_dir} -s solver-test "
                        "-d test-dataset -n 1 --no-plot".split()
                    ], 'benchopt', standalone_mode=False)

        if not raise_install_error:
            out.check_output(
                f"{error.__name__}: important debug message", repetition=1
            )
    finally:
        if prev_value is None:
            del os.environ['BENCHOPT_RAISE_INSTALL_ERROR']
        else:
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
            run([
                str(benchmark.benchmark_dir),
                *'-s test-solver -d test-dataset -n 1 -r 1 --no-plot'.split()
            ], standalone_mode=False)


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
        with CaptureCmdOutput(delete_result_files=False) as out:
            run([
                str(benchmark.benchmark_dir),
                *('-s test-solver -d test-dataset -n 1 -r 1 --no-plot').split()
            ],  standalone_mode=False)
        data = pd.read_parquet(out.result_files[0])
        with open(data.loc[0, "final_results"], "rb") as final_result_file:
            final_results = pickle.load(final_result_file)
    assert final_results == "test_value"


def test_objective_cv_splitter(no_debug_log):

    objective = """from benchopt import BaseObjective
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

    dataset = """from benchopt import BaseDataset
    import numpy as np

    class Dataset(BaseDataset):
        name = "test-dataset"
        def get_data(self):
            return dict(X=np.ones((100, 2)), y=np.zeros(100))
    """

    with temp_benchmark(
                objective=objective, solvers=solver, datasets=dataset
    ) as benchmark:
        print(list(benchmark.benchmark_dir.glob("datasets/*")))
        with CaptureCmdOutput() as out:
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
    with temp_benchmark(
            objective=objective, solvers=solver, datasets=dataset
    ) as benchmark:
        with CaptureCmdOutput() as out:
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

    with temp_benchmark(
            objective=objective, solvers=solver, datasets=dataset
    ) as benchmark:
        with CaptureCmdOutput() as out:
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
    with temp_benchmark(
            objective=objective, solvers=solver, datasets=dataset
    ) as benchmark:
        with CaptureCmdOutput() as out:
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


@pytest.mark.parametrize("n_iter", [1, 2, 5])
def test_run_once_iteration(n_iter):

    solver1 = f"""from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = 'solver1'
        sampling_strategy = 'iteration'

        def set_objective(self, X, y, lmbd): self.run_once({n_iter})
        def run(self, n_iter): print(f"RUNONCE({{n_iter}})")
        def get_result(self): return dict(beta=None)
    """

    with temp_benchmark(solvers=[solver1]) as benchmark:
        with CaptureCmdOutput() as out:
            run([
                str(benchmark.benchmark_dir),
                *'-s solver1 -d test-dataset -n 0 -r 1 --no-plot'.split()
            ], standalone_mode=False)
        out.check_output(rf"RUNONCE\({n_iter}\)", repetition=1)


@pytest.mark.parametrize("n_iter", [1, 2, 5])
def test_run_once_callback(n_iter):

    solver1 = f"""from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = 'solver1'
        sampling_strategy = 'callback'

        def set_objective(self, X, y, lmbd): self.run_once({n_iter})

        def run(self, cb):
            i = 0
            while cb():
                i += 1
            print(f"RUNONCE({{i}})")

        def get_result(self, **data): return dict(beta=None)
    """

    with temp_benchmark(solvers=[solver1]) as benchmark:
        with CaptureCmdOutput() as out:
            run([
                str(benchmark.benchmark_dir),
                *'-s solver1 -d test-dataset -n 0 -r 1 --no-plot'.split()
            ], standalone_mode=False)

        out.check_output(rf"RUNONCE\({n_iter}\)", repetition=1)


@pytest.mark.parametrize("test_case", [
    "no_config", "without_data_home_abs", "with_data_home_abs",
    "without_data_home_rel", "with_data_home_rel"
])
@pytest.mark.parametrize("n_jobs", [1, 2])
def test_paths_config_key(test_case, n_jobs):
    # Need to call resolve to avoid issues with varying drives on Windows
    data_path = Path("/path/to/data").resolve()
    data_home = Path("/path/to/home_data").resolve()
    data_path_rel = Path("path/to/data")

    if test_case == "no_config":
        config = """
        """
        expected_home = "{bench_dir}/data"
        expected_path = f"{expected_home}/dataset"
    elif test_case == "without_data_home_abs":
        config = f"""
            data_paths:
                dataset: {data_path}
        """
        expected_path = str(data_path)
        expected_home = "{bench_dir}/data"
    elif test_case == "without_data_home_rel":
        config = f"""
            data_paths:
                dataset: {data_path_rel}
        """
        expected_home = "{bench_dir}/data"
        expected_path = f"{expected_home}/path/to/data"
    elif test_case == "with_data_home_rel":
        config = f"""
            data_home: {data_home}
            data_paths:
                dataset: {data_path_rel}
        """
        expected_path = str(data_home / data_path_rel)
        expected_home = str(data_home)
    elif test_case == "with_data_home_abs":
        config = f"""
            data_home: {data_home}
            data_paths:
                dataset: {data_path}
        """
        expected_path = str(data_path)
        expected_home = str(data_home)
    else:
        raise Exception("Invalid test case value")

    dataset = """
        from benchopt import BaseDataset
        from benchopt.config import get_data_path

        class Dataset(BaseDataset):
            name = "custom_dataset"
            def get_data(self):
                home = get_data_path()
                path = get_data_path(key="dataset")
                print(f"HOME:{home}")
                print(f"PATH:{path}")

                return dict(X=None, y=None)
    """

    solver = """
        from benchopt import BaseSolver

        class Solver(BaseSolver):
            name = "test-solver"
            def set_objective(self, X, y, lmbd): pass
            def run(self, n_iter): pass
            def get_result(self): return dict(beta=1)
    """

    with temp_benchmark(
            datasets=dataset, solvers=solver, config=config
    ) as bench:
        with CaptureCmdOutput() as out:
            run(
                f"{bench.benchmark_dir} -s test-solver -d custom_dataset "
                f"-n 0 -r 1 --no-plot -j {n_jobs}".split(),
                standalone_mode=False
            )

        expected_home = Path(
            expected_home.format(bench_dir=bench.benchmark_dir.as_posix())
        ).resolve()
        out.check_output(re.escape(f"HOME:{expected_home}"), repetition=1)

        expected_path = Path(
            expected_path.format(bench_dir=bench.benchmark_dir.as_posix())
        ).resolve()
        out.check_output(re.escape(f"PATH:{expected_path}"), repetition=1)


@pytest.mark.parametrize("n_runs,n_reps", [(1, 3), (2, 2), (5, 1)])
def test_warm_up(n_runs, n_reps):
    solver1 = """from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = 'solver1'
        sampling_strategy = 'iteration'
        parameters = {'param': [0, 1]}

        def set_objective(self, X, y, lmbd): pass
        def run(self, n_iter): pass
        def get_result(self, **data): return {'beta': None}

        def warm_up(self):
            print(f"WARMUP#{self.param}")
            self.run_once(1)

    """

    with temp_benchmark(solvers=[solver1]) as benchmark:
        with CaptureCmdOutput() as out:
            run(
                f"{benchmark.benchmark_dir} -s solver1 -d test-dataset "
                f"-n {n_runs} -r {n_reps} --no-plot".split(),
                'benchopt', standalone_mode=False)
        # Make sure warmup is called exactly once
        out.check_output("WARMUP#0", repetition=1)
        out.check_output("WARMUP#1", repetition=1)


@pytest.mark.parametrize("n_runs,n_reps", [(1, 3), (2, 2), (5, 1)])
def test_pre_run_hook(n_runs, n_reps):
    solver1 = """from benchopt import BaseSolver
    from benchopt.stopping_criterion import NoCriterion
    import numpy as np

    class Solver(BaseSolver):
        name = 'solver1'
        stopping_criterion = NoCriterion(strategy='iteration')
        parameters = {'param': [0, 1]}

        def set_objective(self, X, y, lmbd): pass
        def get_result(self): return {'beta': None}

        def pre_run_hook(self, n_iter):
            print(f"PRERUNHOOK({n_iter})#{self.param}")
            self._pre_run_hook_n_iter = n_iter

        def run(self, n_iter):
            assert self._pre_run_hook_n_iter == n_iter

        def get_next(self, stop_val): return stop_val + 1
    """

    with temp_benchmark(solvers=[solver1]) as benchmark:
        with CaptureCmdOutput() as out:
            run(
                f"{benchmark.benchmark_dir} -s solver1 -d test-dataset "
                f"-n {n_runs} -r {n_reps} --no-plot".split(),
                standalone_mode=False
            )

        for id_run in range(n_runs):
            for p in [0, 1]:
                out.check_output(
                    rf"PRERUNHOOK\({id_run}\)#{p}", repetition=n_reps
                )
