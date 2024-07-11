import time
import numpy as np

import pytest

from benchopt.tests import TEST_SOLVER
from benchopt.tests import TEST_DATASET
from benchopt.tests import TEST_OBJECTIVE

from benchopt.tests import SELECT_ONE_PGD
from benchopt.tests import SELECT_ONE_SIMULATED
from benchopt.tests import SELECT_ONE_OBJECTIVE

from benchopt.benchmark import _check_patterns
from benchopt.benchmark import _extract_options
from benchopt.benchmark import _extract_parameters
from benchopt.benchmark import _list_parametrized_classes
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.tests.utils import CaptureRunOutput
from benchopt.cli.main import run


class MockOutput:
    def __init__(self):
        self.reason = None

    def skip(self, reason):
        self.reason = reason


def test_skip_api():

    dataset = TEST_DATASET.get_instance()
    objective = TEST_OBJECTIVE.get_instance(reg=0)
    objective.set_dataset(dataset)

    solver = TEST_SOLVER.get_instance()

    out = MockOutput()
    skip = solver._set_objective(objective, out)
    assert skip
    assert out.reason == 'lmbd=0'

    objective = TEST_OBJECTIVE.get_instance(reg=1)
    objective.set_dataset(dataset)

    out = MockOutput()
    skip = solver._set_objective(objective, out)
    assert not skip
    assert out.reason is None

    dataset = TEST_DATASET.get_instance(skip=True)
    objective = TEST_OBJECTIVE.get_instance()
    skip, reason = objective.set_dataset(dataset)
    assert skip
    assert reason == 'X is all zeros'


def test_get_one_result():
    dataset = TEST_DATASET.get_instance()
    objective = TEST_OBJECTIVE.get_instance()
    objective.set_dataset(dataset)

    one_solution = objective.get_one_result()
    expected = np.zeros(objective.X.shape[1])
    assert all(one_solution['beta'] == expected)


def _assert_parameters_equal(instance, parameters):
    for key, val in parameters.items():
        assert getattr(instance, key) == val


class TEST_DATASET_TWO_PARAMS(TEST_DATASET):
    """Used to test the selection of datasets by keyword parameters."""
    parameters = {'n_samples': [10, 11], 'n_features': [20, 21]}


def test_filter_classes_two_parameters():
    # Test the selection of dataset with optional parameters.

    def filt_(filters):
        return list(_list_parametrized_classes(*_check_patterns(
            [TEST_DATASET_TWO_PARAMS], filters
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


class TEST_DATASET_ONE_PARAM(TEST_DATASET):
    """Used to test the selection of dataset with a positional parameter."""
    parameters = {'n_samples': [10, 11]}


def test_filter_classes_one_param():
    # Test the selection of dataset with only one parameter.

    def filt_(filters):
        return list(_list_parametrized_classes(*_check_patterns(
            [TEST_DATASET_ONE_PARAM], filters
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

    # Special case with a list of tuple parameters
    assert _extract_parameters("'foo, bar'=[(0, 1),(1, 0)]") == \
        {'foo, bar': [(0, 1), (1, 0)]}
    assert _extract_parameters('"foo, bar"=[(0, 1),(1, 0)]') == \
        {'foo, bar': [(0, 1), (1, 0)]}

    for token in [True, False, None]:  # python tokens
        assert _extract_parameters(f"{token}") == [token]
        assert _extract_parameters(f"'{token}'") == [token]
        assert _extract_parameters(f"\"{token}\"") == [token]


def test_error_caching(no_debug_log):

    objective = """from benchopt import BaseObjective

        class Objective(BaseObjective):
            name = "test_obj"
            min_benchopt_version = "0.0.0"

            def set_data(self, X, y): pass
            def get_one_result(self): pass
            def evaluate_result(self, beta): return dict(value=1)
            def get_objective(self): return dict(X=0, y=0)
    """

    solver1 = """from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = "failing-solver"
        sampling_strategy = 'iteration'
        def set_objective(self, X, y): pass
        def run(self, n_iter):
            raise ValueError('Failing solver.')
        def get_result(self): return dict(beta=1)
    """

    solver2 = """from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = "normal-solver"
        sampling_strategy = 'iteration'
        def set_objective(self, X, y): pass
        def run(self, n_iter): pass
        def get_result(self): return dict(beta=1)
    """

    dataset = """from benchopt import BaseDataset

    class Dataset(BaseDataset):
        name = "dataset"
        def get_data(self):
            return dict(X=0, y=1)
    """

    with temp_benchmark(objective=objective,
                        solvers=[solver1, solver2],
                        datasets=[dataset]) as benchmark:
        with CaptureRunOutput() as out:
            for it in range(2):
                run([str(benchmark.benchmark_dir),
                    *' -d dataset --no-plot -r 1 -n 1'.split()],
                    standalone_mode=False)
                # benchmark is too quick to run, without sleep output files
                # have the same name and the unlinking fails:
                if it == 0:
                    time.sleep(1.1)

    # error message should be displayed twice
    out.check_output("ValueError: Failing solver.", repetition=2)


@pytest.mark.parametrize('n_jobs', [1, 2])
def test_benchopt_run_script(n_jobs, no_debug_log):
    from benchopt import run_benchmark

    with temp_benchmark() as benchmark:
        with CaptureRunOutput() as out:
            run_benchmark(
                str(benchmark.benchmark_dir),
                solver_names=[SELECT_ONE_PGD],
                dataset_names=[SELECT_ONE_SIMULATED],
                objective_filters=[SELECT_ONE_OBJECTIVE],
                max_runs=2, n_repetitions=1, n_jobs=n_jobs, plot_result=False
            )

    out.check_output('Simulated', repetition=1)
    out.check_output('Dummy Sparse Regression', repetition=1)
    out.check_output(r'Python-PGD\[step_size=1\]:', repetition=4)
    out.check_output(r'Python-PGD\[step_size=1.5\]:', repetition=0)

    # Make sure the results were saved in a result file
    assert len(out.result_files) == 1, out.output
