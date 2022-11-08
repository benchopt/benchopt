import pytest

from benchopt.tests import DUMMY_BENCHMARK
from benchopt.utils.dynamic_modules import _load_class_from_module


def test_template_dataset():
    # Make sure that importing template_dataset raises an error.
    with pytest.raises(ImportError):
        template_dataset = (
            DUMMY_BENCHMARK.benchmark_dir / 'datasets' / 'template_dataset.py'
        )
        _load_class_from_module(
            template_dataset, 'Dataset', DUMMY_BENCHMARK.benchmark_dir
        )

    # Make sure that this error is not raised when listing all datasets from
    # the benchmark.
    DUMMY_BENCHMARK.get_datasets()


def test_template_solver():
    # Make sure that importing template_dataset raises an error.
    with pytest.raises(ImportError):
        template_dataset = (
            DUMMY_BENCHMARK.benchmark_dir / 'solvers' / 'template_solver.py'
        )
        _load_class_from_module(
            template_dataset, 'Solver', DUMMY_BENCHMARK.benchmark_dir
        )

    # Make sure that this error is not raised when listing all solvers from
    # the benchmark.
    DUMMY_BENCHMARK.get_solvers()