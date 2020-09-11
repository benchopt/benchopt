import sys
import pytest

import numpy as np

from benchopt.base import STOP_STRATEGIES

from benchopt.util import list_benchmark_datasets
from benchopt.util import get_benchmark_objective


def test_benchmark_objective(benchmark_dataset_simu):
    """Check that the objective function and the datasets are well defined."""
    benchmark_name, dataset_class = benchmark_dataset_simu
    objective_class = get_benchmark_objective(benchmark_name)
    objective = objective_class.get_instance()

    dataset = dataset_class.get_instance()
    scale, data = dataset.get_data()
    objective.set_data(**data)

    # check that the reported scale is correct and that the result of
    # the objective function is a scalar
    beta_hat = np.zeros(scale)
    objective_value = objective(beta=beta_hat)
    assert np.isscalar(objective_value), (
        "The output of the objective function should be a scalar."
    )


def test_dataset_class(benchmark_dataset):
    """Check that all dataset_class respects the public API"""
    benchmark_name, dataset_class = benchmark_dataset

    # Check that the dataset_class exposes a name
    assert hasattr(dataset_class, 'name'), "All dataset should expose a name"
    assert isinstance(dataset_class.name, str), (
        "The dataset's name should be a string")

    # Ensure that the dataset exposes a `get_data` function
    # that is callable
    dataset = dataset_class.get_instance()
    assert hasattr(dataset, 'get_data'), (
        "All dataset should implement get_data"
    )
    assert callable(dataset.get_data), (
        "dataset.get_data should be a callable"
    )


def test_dataset_get_data(benchmark_dataset):
    """Check that all installed dataset_class.get_data return the right result
    """
    benchmark_name, dataset_class = benchmark_dataset

    # skip the test if the dataset is not installed
    if not dataset_class.is_installed():
        pytest.skip("Dataset is not installed")

    dataset = dataset_class.get_instance()

    if dataset_class.name.lower() == 'finance':
        pytest.skip("Do not download finance.")

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


def test_solver_class(benchmark_solver):
    """Check that all installed solver_class respects the public API"""

    benchmark_name, solver_class = benchmark_solver

    # Check that the solver_class exposes a name
    assert hasattr(solver_class, 'name'), "All solver should expose a name"
    assert isinstance(solver_class.name, str), (
        "The solver's name should be a string"
    )

    # Check that the solver_class uses a valid stop_strategy
    assert solver_class.stop_strategy in STOP_STRATEGIES


def test_solver_install_api(benchmark_solver):

    _, solver_class = benchmark_solver
    # Check that the solver_class exposes a known install cmd
    assert solver_class.install_cmd in [None, 'conda', 'shell']

    # Check that the solver_class exposes a known install cmd
    if solver_class.install_cmd == 'conda':
        assert hasattr(solver_class, 'requirements')
    if solver_class.install_cmd == 'shell':
        assert hasattr(solver_class, 'install_script')


@pytest.mark.requires_install
def test_solver_install(test_env_name, benchmark_solver):

    benchmark_name, solver_class = benchmark_solver

    if solver_class.name.lower() == 'cyanure' and sys.platform == 'darwin':
        pytest.skip('Cyanure is not easy to install on macos.')

    # assert that install works when forced to reinstalls
    solver_class.install(env_name=test_env_name)
    solver_class.is_installed(env_name=test_env_name,
                              raise_on_not_installed=True)


def test_solver(benchmark_solver):

    benchmark_name, solver_class = benchmark_solver
    if not solver_class.is_installed():
        pytest.skip("Solver is not installed")

    objective_class = get_benchmark_objective(benchmark_name)
    objective = objective_class.get_instance()

    datasets = list_benchmark_datasets(benchmark_name)
    simulated_dataset = [d for d in datasets if d.name.lower() == 'simulated']

    assert len(simulated_dataset) == 1, (
        "All benchmark need to implement a simulated dataset for "
        "testing purpose")

    dataset_class = simulated_dataset[0]
    dataset = dataset_class.get_instance()

    scale, data = dataset.get_data()
    objective.set_data(**data)

    solver = solver_class.get_instance()
    solver.set_objective(**objective.to_dict())
    stop_val = 5000 if solver_class.stop_strategy == 'iteration' else 1e-15
    solver.run(stop_val)
    beta_hat_i = solver.get_result()

    assert beta_hat_i.shape == (scale, )

    val_star = objective(beta_hat_i)

    for _ in range(100):
        eps = 1e-5 * np.random.randn(scale)
        val_eps = objective(beta_hat_i + eps)
        diff = val_eps - val_star
        assert diff > 0
