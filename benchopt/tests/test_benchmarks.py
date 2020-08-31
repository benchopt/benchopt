import sys
import pytest

import numpy as np
from pathlib import Path


from benchopt.base import SAMPLING_STRATEGIES

from benchopt.util import list_benchmark_solvers
from benchopt.util import list_benchmark_datasets
from benchopt.util import get_benchmark_objective


def get_all_benchmarks():
    """List all the available benchmarks.

    Returns
    -------
    benchmarks : list of str
        The list of all available benchmarks.
    """
    BENCHMARKS_DIR = Path(__file__).parents[1] / '..' / 'benchmarks'
    all_benchmarks = [b.resolve() for b in BENCHMARKS_DIR.glob('*/')]
    all_benchmarks.sort()
    return all_benchmarks


BENCHMARKS = get_all_benchmarks()
BENCH_AND_SOLVERS = [
    (benchmark, solver) for benchmark in BENCHMARKS
    for solver in list_benchmark_solvers(benchmark)]
BENCH_AND_DATASETS = [
    (benchmark, dataset_class) for benchmark in BENCHMARKS
    for dataset_class in list_benchmark_datasets(benchmark)]
BENCH_AND_SIMULATED = [
    (benchmark, dataset_class) for benchmark in BENCHMARKS
    for dataset_class in list_benchmark_datasets(benchmark)
    if dataset_class.name.lower() == 'simulated']


def class_ids(parameter):
    if hasattr(parameter, 'name'):
        return parameter.name.lower()
    return None


@pytest.mark.parametrize('benchmark_name, dataset_class', BENCH_AND_SIMULATED,
                         ids=class_ids)
def test_benchmark_objective(benchmark_name, dataset_class):
    """Check that the objective function and the datasets are well defined."""
    objective_class = get_benchmark_objective(benchmark_name)
    objective = objective_class()

    parameters = {}
    dataset = dataset_class(**parameters)
    scale, data = dataset.get_data()
    objective.set_data(**data)

    # check that the reported scale si correct and that the result of
    # the objective function is a scalar
    beta_hat = np.zeros(scale)
    objective_value = objective(beta=beta_hat)
    assert np.isscalar(objective_value), (
        "The output of the objective function should be a scalar."
    )


@pytest.mark.parametrize('benchmark_name, dataset_class', BENCH_AND_DATASETS,
                         ids=class_ids)
def test_dataset_class(benchmark_name, dataset_class):
    """Check that all dataset_class respects the public API"""

    # Check that the dataset_class exposes a name
    assert hasattr(dataset_class, 'name'), "All dataset should expose a name"
    assert isinstance(dataset_class.name, str), (
        "The dataset's name should be a string")

    # Ensure that the dataset exposes a `get_data` function
    # that is callable
    dataset = dataset_class()
    assert hasattr(dataset, 'get_data'), (
        "All dataset should implement get_data"
    )
    assert callable(dataset.get_data), (
        "dataset.get_data should be a callable"
    )


@pytest.mark.parametrize('benchmark_name, dataset_class', BENCH_AND_DATASETS,
                         ids=class_ids)
def test_dataset_get_data(benchmark_name, dataset_class):
    """Check that all installed dataset_class.get_data return the right result
    """
    # skip the test if the dataset is not installed
    if not dataset_class.is_installed():
        pytest.skip("Dataset is not installed")

    dataset = dataset_class()
    data = dataset.get_data()
    assert isinstance(data, tuple), (
        "Output of get_data should be a 2-tuple"
    )
    assert len(data) == 2, (
        "Output of get_data should be a 2-tuple"
    )

    scale, data = data

    assert isinstance(scale, int), (
        "First output of get_data should be integer"
    )
    assert isinstance(data, dict), (
        "Second output of get_data should be dict"
    )


@pytest.mark.parametrize('benchmark_name, solver_class', BENCH_AND_SOLVERS,
                         ids=class_ids)
def test_solver_class(benchmark_name, solver_class):
    """Check that all installed solver_class respects the public API"""

    # Check that the solver_class exposes a name
    assert hasattr(solver_class, 'name'), "All solver should expose a name"
    assert isinstance(solver_class.name, str), (
        "The solver's name should be a string"
    )

    # Check that the solver_class uses a valid sampling_strategy
    assert solver_class.sampling_strategy in SAMPLING_STRATEGIES


@pytest.mark.parametrize('benchmark_name, solver_class', BENCH_AND_SOLVERS,
                         ids=class_ids)
def test_solver_install_api(benchmark_name, solver_class):

    # Check that the solver_class exposes a known install cmd
    assert solver_class.install_cmd in [None, 'conda', 'shell']

    # Check that the solver_class exposes a known install cmd
    if solver_class.install_cmd == 'conda':
        assert hasattr(solver_class, 'requirements')
    if solver_class.install_cmd == 'shell':
        assert hasattr(solver_class, 'install_script')


@pytest.mark.requires_install
@pytest.mark.parametrize('benchmark_name, solver_class', BENCH_AND_SOLVERS,
                         ids=class_ids)
def test_solver_install(test_env_name, benchmark_name, solver_class):

    if solver_class.name.lower() == 'cyanure' and sys.platform == 'darwin':
        pytest.skip('Cyanure is not easy to install on macos.')

    # assert that install works when forced to reinstalls
    solver_class.install(env_name=test_env_name)
    solver_class.is_installed(env_name=test_env_name,
                              raise_on_not_installed=True)


@pytest.mark.parametrize('benchmark_name, solver_class', BENCH_AND_SOLVERS,
                         ids=class_ids)
def test_solver(benchmark_name, solver_class):

    if not solver_class.is_installed():
        pytest.skip("Solver is not installed")

    if 'numba' in solver_class.requirements:
        pytest.skip("_reload create segfault with numba?!")

    # Make sure we get the latest version of the class. As the modules are
    # dynamically created since PR#51, dependencies that are installed in the
    # test can be used to test the solver.
    solver_class = solver_class._reload_class()

    objective_class = get_benchmark_objective(benchmark_name)
    objective = objective_class()

    datasets = list_benchmark_datasets(benchmark_name)
    simulated_dataset = [d for d in datasets if d.name.lower() == 'simulated']

    assert len(simulated_dataset) == 1, (
        "All benchmark need to implement a simulated dataset for "
        "testing purpose")

    dataset_class = simulated_dataset[0]
    dataset = dataset_class()

    scale, data = dataset.get_data()
    objective.set_data(**data)

    solver = solver_class()
    solver.set_objective(**objective.to_dict())
    sample = 1000 if solver_class.sampling_strategy == 'iteration' else 1e-15
    solver.run(sample)
    beta_hat_i = solver.get_result()

    assert beta_hat_i.shape == (scale, )

    val_star = objective(beta_hat_i)

    for _ in range(100):
        eps = 1e-7 * np.random.randn(scale)
        val_eps = objective(beta_hat_i + eps)
        diff = val_eps - val_star
        assert diff > 0
