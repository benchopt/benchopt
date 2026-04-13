from joblib import Parallel, delayed

from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.utils.parametrized_name_mixin import product_param


DATASET = """from benchopt import BaseDataset
    class Dataset(BaseDataset):
        name = "test-dataset"
        parameters = {'n': [1000, 10000], 'seed': [0, 1, 2]}
        # IGNORE
        def get_data(self): return dict(X=None, y=None)
"""


def test_get_prepare_params_no_params():
    # Dataset with no parameters yields exactly one empty dict.
    with temp_benchmark() as bench:
        cls = bench.get_datasets()[0]
        result = list(cls.get_prepare_params())
    assert result == [{}]


def test_get_prepare_params_no_ignore():
    # Without cache_ignore, all parameter combos are yielded independently.
    with temp_benchmark(datasets=DATASET) as bench:
        cls = bench.get_datasets()[0]
        result = list(cls.get_prepare_params())
    # 2 x 3 = 6 combinations, all effective
    assert len(result) == 6
    for effective in result:
        assert set(effective.keys()) == {"n", "seed"}


def test_get_prepare_params_cache_ignore_deduplicates():
    # Params listed in prepare_cache_ignore collapse duplicate combos.
    dataset = DATASET.replace("# IGNORE", "prepare_cache_ignore = ('seed',)")
    with temp_benchmark(datasets=dataset) as bench:
        cls = bench.get_datasets()[0]
        result = list(cls.get_prepare_params())
    # Only 2 unique effective combos (one per value of 'n')
    assert len(result) == 2
    for effective in result:
        assert "seed" not in effective
        assert "n" in effective


def test_get_prepare_params_cache_ignore_all():
    # prepare_cache_ignore='all' yields exactly one job per class.
    dataset = DATASET.replace("# IGNORE", "prepare_cache_ignore = 'all'")
    with temp_benchmark(datasets=dataset) as bench:
        cls = bench.get_datasets()[0]
        result = list(cls.get_prepare_params())
    assert len(result) == 1
    assert result[0] == {}


def test_repr_with_parameter_template():
    # parameter_template overrides the default sorted key=value repr.
    dataset = """from benchopt import BaseDataset
        class Dataset(BaseDataset):
            name = "test-dataset"
            parameters = {'n': [1000], 'seed': [42]}
            parameter_template = "n={n}"
            def get_data(self): return dict(X=None, y=None)
    """
    with temp_benchmark(datasets=dataset) as bench:
        cls = bench.get_datasets()[0]
        instance = cls.get_instance(n=1000, seed=42)
    assert repr(instance) == "test-dataset[n=1000]"


def test_get_instance_saves_params_with_custom_init():
    # get_instance saves parameters even when __init__ is overridden.
    dataset = """from benchopt import BaseDataset
        class Dataset(BaseDataset):
            name = "test-dataset"
            parameters = {'n': [1000, 10000], 'seed': [0, 1]}
            def __init__(self, n=1000, seed=0):
                self.n = n
                self.seed = seed
            def get_data(self): return dict(X=None, y=None)
    """
    with temp_benchmark(datasets=dataset) as bench:
        cls = bench.get_datasets()[0]
        instance = cls.get_instance(n=10000, seed=1)
    assert instance._parameters == {'n': 10000, 'seed': 1}
    assert repr(instance) == "test-dataset[n=10000,seed=1]"


def test_product_param_cartesian_product():
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


def test_product_param_multi_key():
    # Comma-separated keys allow paired parameters to vary together.
    result = list(product_param({'a, b': [(1, 10), (2, 20)]}))
    assert result == [{'a': 1, 'b': 10}, {'a': 2, 'b': 20}]


def test_product_param_mixed():
    # Comma-separated keys allow paired parameters to vary together.
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


def test_pickling_preserves_parameters():
    # Instances can be pickled by joblib and reconstructed with intact
    # parameters (uses __reduce__ -> _load_instance -> _get_mixin_args).
    with temp_benchmark(datasets=DATASET) as bench:
        cls = bench.get_datasets()[0]
        instance = cls.get_instance(n=1000, seed=1)
        reprs = Parallel(n_jobs=2)(
            delayed(repr)(instance) for _ in range(2)
        )
    assert reprs == ["test-dataset[n=1000,seed=1]"] * 2


def test_pickling_does_not_carry_data():
    # Calling _get_data() caches data on the instance as `_data`, but this
    # should not appear in the pickle: the reconstructed instance must be
    # clean so that workers load fresh data rather than inheriting a
    # potentially large cached payload from the parent process.
    dataset = DATASET.replace("# IGNORE", "")
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
