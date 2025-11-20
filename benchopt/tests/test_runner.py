import pytest
import inspect
import pandas as pd

from benchopt import BaseDataset
from benchopt.benchmark import _check_patterns
from benchopt.benchmark import _extract_options
from benchopt.benchmark import _extract_parameters
from benchopt.benchmark import _list_parametrized_classes
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.tests.utils import CaptureCmdOutput
from benchopt.cli.main import run


@pytest.mark.parametrize('n_jobs', [1, 2, 4])
def test_skip_api(n_jobs):

    objective = """from benchopt import BaseObjective

        class Objective(BaseObjective):
            name = "Objective-skip"
            parameters = dict(should_skip=[True, False])

            def skip(self, X, y):
                if self.should_skip:
                    return True, "Objective#SKIP"
                return False, None

            def set_data(self, X, y): self.X, self.y = X, y
            def get_objective(self): return dict(X=1)
            def get_one_result(self): return dict(beta=0)
            def evaluate_result(self, beta): return dict(value=1)
    """

    solver = """from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = "test-solver"
        sampling_strategy = 'run_once'
        parameters = dict(should_skip=[True, False])

        def skip(self, X):
            if self.should_skip:
                return True, "Solver#SKIP"
            return False, None

        def set_objective(self, X): pass
        def run(self, n_iter): print("Solver#RUN")
        def get_result(self): return dict(beta=1)
    """

    with temp_benchmark(objective=objective, solvers=[solver]) as benchmark:
        with CaptureCmdOutput() as out:
            run([*(
                f'{benchmark.benchmark_dir} -s test-solver -d test-dataset '
                f'-j {n_jobs} --no-plot'
            ).split()], standalone_mode=False)

            # Make sure joblib's executor is shutdown, as otherwise the output
            # might be incomplete.
            from joblib.externals.loky import get_reusable_executor
            get_reusable_executor().shutdown(wait=True)

    out.check_output(r"Objective-skip\[should_skip=True\] skip", repetition=1)
    out.check_output("Reason: Objective#SKIP", repetition=1)

    out.check_output(r"test-solver\[should_skip=True\]: skip", repetition=1)
    out.check_output("Reason: Solver#SKIP", repetition=1)

    out.check_output(r"test-solver\[should_skip=False\]: done", repetition=1)
    out.check_output("Solver#RUN", repetition=1)


def _assert_parameters_equal(instance, parameters):
    for key, val in parameters.items():
        assert getattr(instance, key) == val


class _DatasetTwoParams(BaseDataset):
    """Used to test the selection of datasets by keyword parameters."""
    name = "Test-Dataset"
    parameters = {'n_samples': [10, 11], 'n_features': [20, 21]}
    def get_data(self): pass


def test_filter_classes_two_parameters():
    # Test the selection of dataset with optional parameters.

    def filt_(filters):
        return list(_list_parametrized_classes(*_check_patterns(
            [_DatasetTwoParams], filters
        )))

    # no selection (default grid)
    results = filt_(["Test-Dataset"])
    assert len(results) == 4
    _assert_parameters_equal(results[0][0], dict(n_samples=10, n_features=20))
    _assert_parameters_equal(results[1][0], dict(n_samples=10, n_features=21))
    _assert_parameters_equal(results[2][0], dict(n_samples=11, n_features=20))
    _assert_parameters_equal(results[3][0], dict(n_samples=11, n_features=21))

    # select one parameter (n_samples)
    results = filt_(["Test-Dataset[n_samples=42]"])
    assert len(results) == 2
    _assert_parameters_equal(results[0][0], dict(n_samples=42, n_features=20))
    _assert_parameters_equal(results[1][0], dict(n_samples=42, n_features=21))

    # select one parameter (n_features)
    results = filt_(["Test-Dataset[n_features=42]"])
    assert len(results) == 2
    _assert_parameters_equal(results[0][0], dict(n_samples=10, n_features=42))
    _assert_parameters_equal(results[1][0], dict(n_samples=11, n_features=42))

    # select two parameters (n_samples, n_features)
    results = filt_(["Test-Dataset[n_samples=41, n_features=42]"])
    assert len(results) == 1
    _assert_parameters_equal(results[0][0], dict(n_samples=41, n_features=42))

    # get grid over one parameter (n_samples)
    results = filt_(["Test-Dataset[n_samples=[41,42], n_features=19]"])
    assert len(results) == 2
    _assert_parameters_equal(results[0][0], dict(n_samples=41, n_features=19))
    _assert_parameters_equal(results[1][0], dict(n_samples=42, n_features=19))

    # get grid over two parameter (n_samples, n_features)
    results = filt_(["Test-Dataset[n_samples=[41,42], n_features=[19, 20]]"])
    assert len(results) == 4
    _assert_parameters_equal(results[0][0], dict(n_samples=41, n_features=19))
    _assert_parameters_equal(results[1][0], dict(n_samples=41, n_features=20))
    _assert_parameters_equal(results[2][0], dict(n_samples=42, n_features=19))
    _assert_parameters_equal(results[3][0], dict(n_samples=42, n_features=20))

    results = filt_(
        ["Test-Dataset[n_samples=[foo,bar], n_features=[True, False]]"])
    assert len(results) == 4
    _assert_parameters_equal(
        results[0][0], dict(n_samples="foo", n_features=True)
    )
    _assert_parameters_equal(
        results[1][0], dict(n_samples="foo", n_features=False)
    )
    _assert_parameters_equal(
        results[2][0], dict(n_samples="bar", n_features=True)
    )
    _assert_parameters_equal(
        results[3][0], dict(n_samples="bar", n_features=False)
    )
    # get list of tuples
    results = filt_(
        ["Test-Dataset['n_samples, n_features'=[(41, 19), (42, 20)]]"])
    assert len(results) == 2
    _assert_parameters_equal(results[0][0], dict(n_samples=41, n_features=19))
    _assert_parameters_equal(results[1][0], dict(n_samples=42, n_features=20))

    # invalid use of positional parameters
    with pytest.raises(ValueError, match="Ambiguous positional parameter"):
        filt_(["Test-Dataset[41,42]"])

    # invalid use of unknown parameter
    with pytest.raises(ValueError, match="Unknown parameter 'n_targets'"):
        filt_(["Test-Dataset[n_targets=42]"])


class _DatasetOneParam(BaseDataset):
    """Used to test the selection of dataset with a positional parameter."""
    name = "Test-Dataset"
    parameters = {'n_samples': [10, 11]}
    def get_data(self): pass


def test_filter_classes_one_param():
    # Test the selection of dataset with only one parameter.

    def filt_(filters):
        return list(_list_parametrized_classes(*_check_patterns(
            [_DatasetOneParam], filters
        )))

    # test positional parameter
    results = filt_(["Test-Dataset[42]"])
    assert len(results) == 1
    _assert_parameters_equal(results[0][0], dict(n_samples=42))

    # test grid of positional parameter
    results = filt_(["Test-Dataset[41,42]"])
    assert len(results) == 2
    _assert_parameters_equal(results[0][0], dict(n_samples=41))
    _assert_parameters_equal(results[1][0], dict(n_samples=42))

    results = filt_(["Test-Dataset[foo, 'bar', None]"])
    assert len(results) == 3
    _assert_parameters_equal(results[0][0], dict(n_samples="foo"))
    _assert_parameters_equal(results[1][0], dict(n_samples="bar"))
    _assert_parameters_equal(results[2][0], dict(n_samples=None))

    # test grid of keyword parameter
    results = filt_(["Test-Dataset[n_samples=[foo,True]]"])
    assert len(results) == 2
    _assert_parameters_equal(results[0][0], dict(n_samples="foo"))
    _assert_parameters_equal(results[1][0], dict(n_samples=True))

    # invalid use of both positional and keyword parameter
    with pytest.raises(ValueError, match="Invalid name"):
        filt_(["Test-Dataset[41, n_samples=42]"])


def test_extract_options():
    basename, args, kwargs = _extract_options("Dataset")
    assert basename == "Dataset"
    assert len(args) == 0
    assert kwargs == dict()

    basename, args, kwargs = _extract_options("Test-Dataset[n_samples=41]")
    assert basename == "Test-Dataset"
    assert len(args) == 0
    assert kwargs == dict(n_samples=41)

    basename, args, kwargs = _extract_options("n_samples[n_samples=41,]")
    assert basename == "n_samples"
    assert len(args) == 0
    assert kwargs == dict(n_samples=41)

    basename, args, kwargs = _extract_options(
        "Dataset[n_samples=[41, 42], n_features=123.0]")
    assert basename == "Dataset"
    assert len(args) == 0
    assert kwargs == dict(n_samples=[41, 42], n_features=123.)

    with pytest.raises(ValueError, match="Invalid name"):
        _extract_options("Dataset[n_samples=42")  # missing "]"
    with pytest.raises(ValueError, match="Invalid name"):
        _extract_options("Dataset[n_samples=[41, 42]")  # missing "]"


def test_extract_parameters():
    # Test the conversion of parameters.

    # Convert to a list
    assert _extract_parameters("42") == [42]
    assert _extract_parameters("True") == [True]
    assert _extract_parameters("foo") == ["foo"]
    assert _extract_parameters("foo-bar") == ["foo-bar"]
    assert _extract_parameters("foo.bar") == ["foo.bar"]
    assert _extract_parameters("1, 2, 3") == [1, 2, 3]
    assert _extract_parameters("1e1, -.1e-3, 12.e+1") == [10.0, -0.0001, 120.0]
    assert _extract_parameters("foo42e1, bar1.0e4") == ["foo42e1", "bar1.0e4"]
    assert _extract_parameters("foo_4e2, bar01e3") == ["foo_4e2", "bar01e3"]

    assert _extract_parameters("42, True, foo") == [42, True, "foo"]
    assert _extract_parameters("42, (1, 2, 3)") == [42, (1, 2, 3)]
    assert _extract_parameters("foo,bar ") == ["foo", "bar"]
    assert _extract_parameters("foo, bar") == ["foo", "bar"]
    assert _extract_parameters("foo,bar,") == ["foo", "bar"]
    assert _extract_parameters("'foo, bar'") == ["foo, bar"]
    assert _extract_parameters('"foo, bar"') == ["foo, bar"]
    assert _extract_parameters("foo, (bar, baz)") == ["foo", ("bar", "baz")]

    # Convert to a dict
    assert _extract_parameters("foo=(bar, baz)") == {'foo': ('bar', 'baz')}
    assert _extract_parameters("foo=(0, 1),bar=2") == {'foo': (0, 1), 'bar': 2}
    assert _extract_parameters("foo=[100, 200]") == {'foo': [100, 200]}
    assert _extract_parameters("foo=/path/to/my-file,bar=baz") == \
        {'foo': '/path/to/my-file', 'bar': 'baz'}
    assert _extract_parameters("foo=[\\path\\to\\file,other\\path]") == \
        {'foo': ['\\path\\to\\file', 'other\\path']}

    # Special case with a list of tuple parameters
    assert _extract_parameters("'foo, bar'=[(0, 1),(1, 0)]") == \
        {'foo, bar': [(0, 1), (1, 0)]}
    assert _extract_parameters('"foo, bar"=[(0, 1),(1, 0)]') == \
        {'foo, bar': [(0, 1), (1, 0)]}

    for token in [True, False, None]:  # python tokens
        assert _extract_parameters(f"{token}") == [token]
        assert _extract_parameters(f"'{token}'") == [token]
        assert _extract_parameters(f"\"{token}\"") == [token]


# Under windows, the function needs to be pickleable
# for parallel jobs to work with joblib
@pytest.mark.parametrize('n_jobs', [1, 2])
def test_benchopt_run_script(n_jobs, no_debug_log):
    from benchopt import run_benchmark

    with temp_benchmark() as benchmark:
        with CaptureCmdOutput() as out:
            run_benchmark(
                str(benchmark.benchmark_dir),
                solver_names=["test-solver"],
                dataset_names=["simulated"],
                max_runs=2, n_repetitions=1, n_jobs=n_jobs, plot_result=False
            )

    out.check_output('simulated', repetition=1)
    out.check_output('test-objective', repetition=1)
    out.check_output('test-solver:', repetition=4)
    out.check_output('template_solver:', repetition=0)

    # Make sure the results were saved in a result file
    assert len(out.result_files) == 1, out.output


def test_prefix_with_same_parameters():
    from benchopt import run_benchmark

    solver1 = """from benchopt import BaseSolver

        class Solver(BaseSolver):
            name = "solver1"
            sampling_strategy = 'iteration'
            parameters = dict(seed=[3, 27])
            def set_objective(self, X, y): pass
            def run(self, n_iter): pass
            def get_result(self): return dict(beta=1)
    """

    # Different name and extra parameter
    solver2 = (
        solver1.replace("solver1", "solver2")
        .replace('seed=[3, 27]', 'seed=[2, 28], type=["s"]')
    )

    dataset1 = """from benchopt import BaseDataset

        class Dataset(BaseDataset):
            name = "dataset1"
            parameters = dict(seed=[3, 27])
            def get_data(self):
                return dict(X=0, y=1)
    """

    # Different name and extra parameter
    dataset2 = (
        dataset1.replace("dataset1", "dataset2")
        .replace('seed=[3, 27]', 'seed=[2, 28], type=["d"]')
    )

    objective = """from benchopt import BaseObjective

        class Objective(BaseObjective):
            name = "test_obj"
            min_benchopt_version = "0.0.0"

            parameters = dict(test_p=[4])
            def set_data(self, X, y): pass
            def get_one_result(self): pass
            def evaluate_result(self, beta): return dict(value=1)
            def get_objective(self): return dict(X=0, y=0)
    """

    with temp_benchmark(solvers=[solver1, solver2],
                        datasets=[dataset1, dataset2],
                        objective=objective
                        ) as benchmark:
        run_benchmark(
            str(benchmark.benchmark_dir),
            solver_names=["solver1", "solver2"],
            dataset_names=["dataset1", "dataset2"],
            max_runs=1, n_repetitions=1, n_jobs=1, plot_result=False
        )

        df = pd.read_parquet(benchmark.get_result_file())

        assert "p_solver_seed" in df.columns
        assert "p_solver_type" in df.columns
        assert "p_dataset_seed" in df.columns
        assert "p_dataset_type" in df.columns
        assert "p_obj_test_p" in df.columns

        assert df.query("p_solver_seed.isna()").shape[0] == 0
        no_type = df.query("p_solver_type.isna()")['solver_name'].unique()
        assert all('solver1' in s for s in no_type)

        assert df.query("p_dataset_seed.isna()").shape[0] == 0
        no_type = df.query("p_dataset_type.isna()")['dataset_name'].unique()
        assert all('dataset1' in s for s in no_type)

        assert df.query("p_obj_test_p.isna()").shape[0] == 0

        # No mixing
        assert "d" not in df['p_solver_type'].unique()
        assert "s" in df['p_solver_type'].unique()
        assert "s" not in df['p_dataset_type'].unique()
        assert "d" in df['p_dataset_type'].unique()


def test_warmup_error(no_debug_log):
    # Non-regression test for benchopt/benchopt#808
    from benchopt import run_benchmark

    solver = """from benchopt import BaseSolver

        class Solver(BaseSolver):
            name = "solver1"
            sampling_strategy = 'iteration'
            def warm_up(self): raise RuntimeError("Warmup error")
            def set_objective(self, X, y, lmbd): pass
            def run(self, n_iter): pass
            def get_result(self): return dict(beta=1)
    """

    with temp_benchmark(solvers=solver) as benchmark:
        with CaptureCmdOutput() as out, pytest.raises(RuntimeError):
            run_benchmark(
                str(benchmark.benchmark_dir),
                solver_names=["solver1"],
                dataset_names=["test-dataset"],
                max_runs=1, n_repetitions=1, n_jobs=1, plot_result=False
            )
        out.check_output("RuntimeError: Warmup error", repetition=1)
        out.check_output("UnboundLocalError", repetition=0)
        out.check_output("No output produced.", repetition=1)


class TestCache:
    """Test the cache of the benchmark."""

    objective = """from benchopt import BaseObjective

        class Objective(BaseObjective):
            name = "test_obj"
            min_benchopt_version = "0.0.0"

            def set_data(self, X, y): pass
            def get_one_result(self): pass
            def evaluate_result(self, beta): return dict(value=1)
            def get_objective(self): return dict(X=0, y=0)
    """

    solver = """from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = "test-solver"
        sampling_strategy = 'run_once'
        def set_objective(self, X, y): pass
        def run(self, _): print("#RUN_SOLVER")
        def get_result(self): return dict(beta=1)
    """

    dataset = """from benchopt import BaseDataset

    class Dataset(BaseDataset):
        name = "test-dataset"
        def get_data(self): return dict(X=0, y=1)
    """

    @pytest.mark.parametrize('n_reps', [1, 4])
    def test_cache(self, no_debug_log, n_reps):
        with temp_benchmark(
                objective=self.objective, solvers=self.solver,
                datasets=self.dataset
        ) as bench:
            with CaptureCmdOutput() as out:
                for it in range(3):
                    run(f"{bench.benchmark_dir} --no-plot -r {n_reps}".split(),
                        standalone_mode=False)

        # Check that the run are only call once per repetition, but not cached
        # when using multiple repetitions
        out.check_output("#RUN_SOLVER", repetition=n_reps)

    @pytest.mark.parametrize('n_reps', [1, 4])
    def test_no_cache(self, no_debug_log, n_reps):
        with temp_benchmark(
                objective=self.objective, solvers=self.solver,
                datasets=self.dataset
        ) as bench:
            with CaptureCmdOutput() as out:
                for it in range(3):
                    run(f"{bench.benchmark_dir} --no-plot -r {n_reps} "
                        "--no-cache".split(), standalone_mode=False)

        # Check that the run is not cached when using --no-cache
        out.check_output("#RUN_SOLVER", repetition=n_reps * 3)

    def test_no_error_caching(self, no_debug_log):

        solver_fail = """from benchopt import BaseSolver

        class Solver(BaseSolver):
            name = "failing-solver"
            sampling_strategy = 'iteration'
            def set_objective(self, X, y): pass
            def run(self, n_iter):
                raise ValueError('Failing solver.')
            def get_result(self): return dict(beta=1)
        """

        with temp_benchmark(objective=self.objective,
                            solvers=[self.solver, solver_fail],
                            datasets=self.dataset) as bench:
            with CaptureCmdOutput() as out:
                for it in range(3):
                    run(f"{bench.benchmark_dir} --no-plot -r 1 -n 1".split(),
                        standalone_mode=False)

        # error message should be displayed twice
        out.check_output("ValueError: Failing solver.", repetition=3)

    @pytest.mark.parametrize('n_reps', [1, 4])
    def test_cache_order(self, no_debug_log, n_reps):
        with temp_benchmark(
                objective=self.objective, datasets=self.dataset,
                solvers=[
                    self.solver,
                    self.solver.replace("test-solver", "test-solver2")
                    .replace("#RUN_SOLVER", "#RUN_2SOLVER")
                ]
        ) as bench:
            with CaptureCmdOutput() as out:
                run([str(bench.benchmark_dir),
                     *"-s test-solver -s test-solver2 "
                     f'--no-plot -r {n_reps}'.split()],
                    standalone_mode=False)
                run([str(bench.benchmark_dir),
                     *"-s test-solver2 -s test-solver "
                    f'--no-plot -r {n_reps}'.split()],
                    standalone_mode=False)

        # Check that the run are only call once per repetition, but not cached
        # when using multiple repetitions
        out.check_output("#RUN_SOLVER", repetition=n_reps)
        out.check_output("#RUN_2SOLVER", repetition=n_reps)

    @pytest.mark.parametrize('n_reps', [1, 4])
    def test_cache_invalid(self, no_debug_log, n_reps):
        with temp_benchmark(
                objective=self.objective, datasets=self.dataset,
                solvers=self.solver,
        ) as bench:
            with CaptureCmdOutput() as out:
                run(f"{bench.benchmark_dir} --no-plot -r {n_reps}".split(),
                    standalone_mode=False)
                # Modify the solver, to make the cache invalid
                solver_file = bench.benchmark_dir / 'solvers' / 'solver_0.py'
                modified_solver = inspect.cleandoc(self.solver.replace(
                    "#RUN_SOLVER", "#RUN_SOLVER_MODIFIED"
                ))
                assert solver_file.exists()
                solver_file.write_text(inspect.cleandoc(modified_solver))

                run(f"{bench.benchmark_dir} --no-plot -r {n_reps} -j2".split(),
                    standalone_mode=False)

        # Check that the 2nd run is not cached and the cache is invalidated.
        out.check_output("#RUN_SOLVER_MODIFIED", repetition=n_reps)
