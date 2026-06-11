from benchopt.utils.temp_benchmark import temp_benchmark


def test_dataset_name_default():
    # When test_dataset_name is None (the default), get_test_dataset_names
    # picks the sole dataset for single-dataset benchmarks, and falls back
    # to 'simulated' when multiple datasets are available.
    only_data = """from benchopt import BaseDataset
    class Dataset(BaseDataset):
        name = "only-data"
        def get_data(self):
            print("Selected#only-data")
            return dict(X=None, y=None)
    """
    # For a benchmark with a single dataset, test_datset_name is this dataset
    with temp_benchmark(datasets=only_data) as bench:
        assert bench.get_test_dataset_names() == ['only-data']

    # For a benchmark with multiple datasets, default is 'simulated'.
    # temp_benchmark add a simulated dataset by default when passed a dict.
    with temp_benchmark(datasets={'only-data': only_data}) as bench:
        assert bench.get_test_dataset_names() == ['simulated']
