import pytest
from joblib import Parallel, delayed

from benchopt import BaseDataset
from benchopt.benchmark import _list_parametrized_classes
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.utils.parametrized_name_mixin import product_param
from benchopt.utils.parametrized_name_mixin import _check_patterns
from benchopt.utils.parametrized_name_mixin import _get_used_parameters
from benchopt.utils.parametrized_name_mixin import _extract_options
from benchopt.utils.parametrized_name_mixin import _extract_parameters


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
        assert _extract_parameters(f'"{token}"') == [token]


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


class TestProductParam:

    def test_cartesian_product(self):
        # product_param yields the cartesian product of all parameter lists.
        result = list(product_param({'a': [1, 2], 'b': [10, 20, 30]}))
        assert result == [
            {'a': 1, 'b': 10},
            {'a': 1, 'b': 20},
            {'a': 1, 'b': 30},
            {'a': 2, 'b': 10},
            {'a': 2, 'b': 20},
            {'a': 2, 'b': 30},
        ]

    def test_multi_key(self):
        # Comma-separated keys allow paired parameters to vary together.
        result = list(product_param({'a, b': [(1, 10), (2, 20)]}))
        assert result == [{'a': 1, 'b': 10}, {'a': 2, 'b': 20}]

    def test_mixed(self):
        # Comma-separated keys combine with independent keys via product.
        result = list(product_param({
            'a, b': [(1, 10), (2, 20)],
            'c': [100, 200],
        }))
        assert result == [
            {'a': 1, 'b': 10, 'c': 100},
            {'a': 1, 'b': 10, 'c': 200},
            {'a': 2, 'b': 20, 'c': 100},
            {'a': 2, 'b': 20, 'c': 200}
        ]


class TestGetUsedParameters:

    def test_no_params(self):
        # Class with no parameters yields exactly one empty dict.
        class _Cls:
            parameters = {}
        result = list(_get_used_parameters(_Cls, {}))
        assert result == [{}]

    def test_no_ignore(self):
        # Without ignore, all parameter combos are yielded independently.
        class _Cls:
            parameters = {'n': [1000, 10000], 'seed': [0, 1, 2]}
        result = list(_get_used_parameters(_Cls, _Cls.parameters))
        # 2 x 3 = 6 combinations
        assert len(result) == 6
        for params in result:
            assert set(params.keys()) == {'n', 'seed'}

    def test_invalid(self):
        class _Cls:
            parameters = {'n': [1000, 10000], 'seed': [0, 1, 2]}

        with pytest.raises(ValueError, match=r"Unknown parameters.*'invalid'"):
            list(_get_used_parameters(_Cls, {'invalid': [0]}))

    def test_ignore_deduplicates(self):
        # Parameters listed in ignore collapse duplicate combos.
        class _Cls:
            parameters = {'n': [1000, 10000], 'seed': [0, 1, 2]}
        result = list(_get_used_parameters(
            _Cls, _Cls.parameters, ignore=('seed',)
        ))
        # Only 2 unique combos (one per value of 'n'), 'seed' excluded
        assert len(result) == 2
        for params in result:
            assert 'seed' not in params
            assert 'n' in params


class TestCheckPatterns:

    class _DatasetTwoParams(BaseDataset):
        """Datasets selection with keyword parameters."""
        name = "Test-Dataset"
        parameters = {'n_samples': [10, 11], 'n_features': [20, 21]}
        def get_data(self): pass

    class _DatasetOneParam(BaseDataset):
        """Dataset selection dataset with positional parameter."""
        name = "Test-Dataset"
        parameters = {'n_samples': [10, 11]}
        def get_data(self): pass

    def test_two_parameters(self):
        # Test the selection of dataset with optional parameters.

        def filt_(filters):
            return list(_list_parametrized_classes(*_check_patterns(
                [self._DatasetTwoParams], filters
            )))

        def assert_eq(instance, params):
            for key, val in params.items():
                assert getattr(instance, key) == val

        # no selection (default grid)
        results = filt_(["Test-Dataset"])
        assert len(results) == 4
        assert_eq(results[0][0], dict(n_samples=10, n_features=20))
        assert_eq(results[1][0], dict(n_samples=10, n_features=21))
        assert_eq(results[2][0], dict(n_samples=11, n_features=20))
        assert_eq(results[3][0], dict(n_samples=11, n_features=21))

        # select one parameter (n_samples)
        results = filt_(["Test-Dataset[n_samples=42]"])
        assert len(results) == 2
        assert_eq(results[0][0], dict(n_samples=42, n_features=20))
        assert_eq(results[1][0], dict(n_samples=42, n_features=21))

        # select one parameter (n_features)
        results = filt_(["Test-Dataset[n_features=42]"])
        assert len(results) == 2
        assert_eq(results[0][0], dict(n_samples=10, n_features=42))
        assert_eq(results[1][0], dict(n_samples=11, n_features=42))

        # select two parameters (n_samples, n_features)
        results = filt_(["Test-Dataset[n_samples=41, n_features=42]"])
        assert len(results) == 1
        assert_eq(results[0][0], dict(n_samples=41, n_features=42))

        # get grid over one parameter (n_samples)
        results = filt_(["Test-Dataset[n_samples=[41,42], n_features=19]"])
        assert len(results) == 2
        assert_eq(results[0][0], dict(n_samples=41, n_features=19))
        assert_eq(results[1][0], dict(n_samples=42, n_features=19))

        # get grid over two parameter (n_samples, n_features)
        results = filt_([
            "Test-Dataset[n_samples=[41,42], n_features=[19, 20]]"
        ])
        assert len(results) == 4
        assert_eq(results[0][0], dict(n_samples=41, n_features=19))
        assert_eq(results[1][0], dict(n_samples=41, n_features=20))
        assert_eq(results[2][0], dict(n_samples=42, n_features=19))
        assert_eq(results[3][0], dict(n_samples=42, n_features=20))

        results = filt_(
            ["Test-Dataset[n_samples=[foo,bar], n_features=[True, False]]"])
        assert len(results) == 4
        assert_eq(results[0][0], dict(n_samples="foo", n_features=True))
        assert_eq(results[1][0], dict(n_samples="foo", n_features=False))
        assert_eq(results[2][0], dict(n_samples="bar", n_features=True))
        assert_eq(results[3][0], dict(n_samples="bar", n_features=False))

        # get list of tuples
        results = filt_(
            ["Test-Dataset['n_samples, n_features'=[(41, 19), (42, 20)]]"])
        assert len(results) == 2
        assert_eq(results[0][0], dict(n_samples=41, n_features=19))
        assert_eq(results[1][0], dict(n_samples=42, n_features=20))

        # invalid use of positional parameters
        with pytest.raises(ValueError, match="Ambiguous positional parameter"):
            filt_(["Test-Dataset[41,42]"])

        # invalid use of unknown parameter
        with pytest.raises(ValueError, match="Unknown parameter 'n_targets'"):
            filt_(["Test-Dataset[n_targets=42]"])

    def test_one_param(self):
        # Test the selection of dataset with only one parameter.

        def filt_(filters):
            return list(_list_parametrized_classes(*_check_patterns(
                [self._DatasetOneParam], filters
            )))

        def assert_eq(instance, params):
            for key, val in params.items():
                assert getattr(instance, key) == val

        # test positional parameter
        results = filt_(["Test-Dataset[42]"])
        assert len(results) == 1
        assert_eq(results[0][0], dict(n_samples=42))

        # test grid of positional parameter
        results = filt_(["Test-Dataset[41,42]"])
        assert len(results) == 2
        assert_eq(results[0][0], dict(n_samples=41))
        assert_eq(results[1][0], dict(n_samples=42))

        results = filt_(["Test-Dataset[foo, 'bar', None]"])
        assert len(results) == 3
        assert_eq(results[0][0], dict(n_samples="foo"))
        assert_eq(results[1][0], dict(n_samples="bar"))
        assert_eq(results[2][0], dict(n_samples=None))

        # test grid of keyword parameter
        results = filt_(["Test-Dataset[n_samples=[foo,True]]"])
        assert len(results) == 2
        assert_eq(results[0][0], dict(n_samples="foo"))
        assert_eq(results[1][0], dict(n_samples=True))

        # invalid use of both positional and keyword parameter
        with pytest.raises(ValueError, match="Invalid name"):
            filt_(["Test-Dataset[41, n_samples=42]"])


class TestParametrizedNameMixin:

    dataset = """from benchopt import BaseDataset
        class Dataset(BaseDataset):
            name = "test-dataset"
            parameters = {'n': [1000, 10000], 'seed': [0, 1, 2]}
            # CUSTOM
            def get_data(self): return dict(X=None, y=None)
    """

    def test_repr_with_parameter_template(self):
        # parameter_template overrides the default sorted key=value repr.
        dataset = self.dataset.replace(
            "# CUSTOM", "parameter_template = 'n={n}'"
        )
        with temp_benchmark(datasets=dataset) as bench:
            cls = bench.get_datasets()[0]
            instance = cls.get_instance(n=1000, seed=42)
        assert repr(instance) == "test-dataset[n=1000]"

    def test_get_instance_saves_params_with_custom_init(self):
        # get_instance saves parameters even when __init__ is overridden.
        dataset = self.dataset.replace(
            "# CUSTOM",
            "def __init__(self, n, seed): self.n, self.seed = 1, 2"
        )
        with temp_benchmark(datasets=dataset) as bench:
            cls = bench.get_datasets()[0]
            instance = cls.get_instance(n=10000, seed=1)
        assert instance.n == 1
        assert instance._parameters == {'n': 10000, 'seed': 1}
        assert repr(instance) == "test-dataset[n=10000,seed=1]"

    def test_pickling_preserves_parameters(self):
        # Instances can be pickled by joblib and reconstructed with intact
        # parameters (uses __reduce__ -> _load_instance -> _get_mixin_args).
        with temp_benchmark(datasets=self.dataset) as bench:
            cls = bench.get_datasets()[0]
            instance = cls.get_instance(n=1000, seed=1)
            reprs = Parallel(n_jobs=2)(
                delayed(repr)(instance) for _ in range(2)
            )
        assert reprs == ["test-dataset[n=1000,seed=1]"] * 2

    def test_pickling_does_not_carry_data(self):
        # Calling _get_data() caches data on the instance as `_data`, but this
        # should not appear in the pickle: the reconstructed instance must be
        # clean so that workers load fresh data rather than inheriting a
        # potentially large cached payload from the parent process.
        dataset = self.dataset.replace("# CUSTOM", "")
        with temp_benchmark(datasets=dataset) as bench:
            cls = bench.get_datasets()[0]
            instance = cls.get_instance(n=1000, seed=1)
            # Populate the in-process cache
            instance._get_data()
            assert hasattr(instance, '_data')

            has_data = Parallel(n_jobs=2)(
                delayed(hasattr)(instance, '_data') for _ in range(2)
            )
        # Workers reconstruct via _load_instance, which does not carry _data
        assert has_data == [False, False]
