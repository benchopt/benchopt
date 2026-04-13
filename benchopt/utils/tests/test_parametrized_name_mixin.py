from benchopt.utils.temp_benchmark import temp_benchmark


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
