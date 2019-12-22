import pytest
import numpy as np

from benchopt.util import get_all_benchmarks
from benchopt.util import load_benchmark_losses


BENCHMARKS = get_all_benchmarks()


@pytest.mark.parametrize('benchmark_name', BENCHMARKS)
def test_benchmark(benchmark_name):
    """Check that the loss function and the datasets are well defined."""
    loss_function, datasets = load_benchmark_losses(benchmark_name)

    for dataset_name, (get_data, parameters) in datasets.items():
        scale, *loss_parameters = get_data(**parameters)

        # check that the reported scale si correct and that the result of
        # the loss function is a scalar
        beta_hat = np.zeros(scale)
        assert np.isscalar(loss_function(*loss_parameters, beta_hat)), (
            "The output of the loss function should be a scalar."
        )
