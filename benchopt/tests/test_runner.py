import numpy as np

import pytest

from benchopt.tests import TEST_SOLVER
from benchopt.tests import TEST_DATASET
from benchopt.tests import TEST_OBJECTIVE
from benchopt.benchmark import _filter_classes
from benchopt.benchmark import _extract_options
from benchopt.benchmark import _extract_parameters


def test_skip_api():

    dataset = TEST_DATASET.get_instance()
    objective = TEST_OBJECTIVE.get_instance(reg=0)
    objective.set_dataset(dataset)

    solver = TEST_SOLVER.get_instance()

    skip, reason = solver._set_objective(objective)
    assert skip
    assert reason == 'lmbd=0'

    objective = TEST_OBJECTIVE.get_instance(reg=1)
    objective.set_dataset(dataset)

    skip, reason = solver._set_objective(objective)
    assert not skip
    assert reason is None

    dataset = TEST_DATASET.get_instance(skip=True)
    objective = TEST_OBJECTIVE.get_instance()
    skip, reason = objective.set_dataset(dataset)
    assert skip
    assert reason == 'X is all zeros'


def test_get_one_solution():
    dataset = TEST_DATASET.get_instance()
    objective = TEST_OBJECTIVE.get_instance()
    objective.set_dataset(dataset)

    one_solution = objective.get_one_solution()
    expected = np.zeros(objective.X.shape[1])
    assert all(one_solution == expected)

    # XXX - Remove in version 1.3
    dataset = TEST_DATASET.get_instance(deprecated_return=True)
    objective = TEST_OBJECTIVE.get_instance(deprecated_dataset=True)

    with pytest.warns(FutureWarning, match="`get_data` should return a dict"):
        objective.set_dataset(dataset)

    with pytest.warns(FutureWarning, match="Objective should have a method"):
        one_solution = objective.get_one_solution()
    expected = np.zeros(objective.X.shape[1])
    assert all(one_solution == expected)


def _assert_parameters_equal(instance, parameters):
    for key, val in parameters.items():
        assert getattr(instance, key) == val


class TEST_DATASET_KEYWORDS(TEST_DATASET):
    """Used to test the selection of datasets by keyword parameters."""
    parameters = {'n_samples': [10, 11], 'n_features': [20, 21]}


def test_filter_classes_parameters():
    # Test the selection of dataset with optional parameters.

    def filt_(filters):
        return list(_filter_classes(TEST_DATASET_KEYWORDS, filters=filters))

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

    # get list of tuples
    results = filt_(["Test-Dataset['n_samples, n_features'"
                     "=[(41, 19), (42, 20)]]"])
    assert len(results) == 2
    _assert_parameters_equal(results[0][0], dict(n_samples=41, n_features=19))
    _assert_parameters_equal(results[1][0], dict(n_samples=42, n_features=20))

    # invalid use of positional parameters
    with pytest.raises(ValueError, match="Ambiguous positional parameter"):
        filt_(["Test-Dataset[41,42]"])

    # invalid use of unknown parameter
    with pytest.raises(ValueError, match="Unknown parameter 'n_targets'"):
        filt_(["Test-Dataset[n_targets=42]"])


class TEST_DATASET_POSITIONAL(TEST_DATASET):
    """Used to test the selection of dataset with a positional parameter."""
    parameters = {'n_samples': [10, 11]}


def test_filter_classes_positional():
    # Test the selection of dataset with a positional parameter.

    def filt_(filters):
        return list(_filter_classes(TEST_DATASET_POSITIONAL, filters=filters))

    results = filt_(["Test-Dataset[42]"])
    assert len(results) == 1
    _assert_parameters_equal(results[0][0], dict(n_samples=42))

    results = filt_(["Test-Dataset[41,42]"])
    assert len(results) == 2
    _assert_parameters_equal(results[0][0], dict(n_samples=41))
    _assert_parameters_equal(results[1][0], dict(n_samples=42))

    # test recursive eval within list, to eval strings
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
    assert _extract_parameters("1, 2, 3") == [1, 2, 3]

    assert _extract_parameters("42, True, foo") == [42, True, "foo"]
    assert _extract_parameters("42, (1, 2, 3)") == [42, (1, 2, 3)]
    assert _extract_parameters("foo,bar ") == ["foo", "bar"]
    assert _extract_parameters("foo, bar") == ["foo", "bar"]
    assert _extract_parameters("foo,bar,") == ["foo", "bar"]
    assert _extract_parameters("foo, (bar, baz)") == ["foo", ("bar", "baz")]

    # Convert to a dict
    assert _extract_parameters("foo=(bar, baz)") == {'foo': ('bar', 'baz')}
    assert _extract_parameters("foo=(0, 1),bar=2") == {'foo': (0, 1), 'bar': 2}

    # Special case with a list of tuple parameters
    assert _extract_parameters("'foo, bar'=[(0, 1),(1, 0)]") == \
        {'foo, bar': [(0, 1), (1, 0)]}
