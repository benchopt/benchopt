import sys
import pytest
import numbers

import numpy as np

from benchopt.base import STOP_STRATEGIES
from benchopt.runner import _Callback
from benchopt.stopping_criterion import StoppingCriterion


def test_benchmark_objective(benchmark, dataset_simu):
    """Check that the objective function and the datasets are well defined."""
    objective_class = benchmark.get_benchmark_objective()
    objective = objective_class.get_instance()

    dataset = dataset_simu.get_instance()
    dimension, data = dataset._get_data()
    objective.set_data(**data)

    # check that the reported dimension is correct and that the result of
    # the objective function is a dictionary containing a scalar value for
    # `objective_value`.
    beta_hat = np.zeros(*dimension)
    objective_dict = objective(beta_hat)

    assert 'objective_value' in objective_dict, (
        'When the output of objective is a dict, it should at least contain '
        'a value associated to `objective_value` which will be used to detect '
        'the convergence of the algorithm.'
    )
    assert np.isscalar(objective_dict['objective_value']), (
        "The output of the objective function should be a scalar, or a dict "
        "containing a scalar associated to `objective_value`."
    )


def test_dataset_class(benchmark, dataset_class):
    """Check that all dataset_class respects the public API"""

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


def test_dataset_get_data(benchmark, dataset_class):
    """Check that all installed dataset_class.get_data return the right result
    """

    # skip the test if the dataset is not installed
    if not dataset_class.is_installed():
        pytest.skip("Dataset is not installed")

    dataset = dataset_class.get_instance()

    if dataset_class.name.lower() == 'finance':
        pytest.skip("Do not download finance.")

    res = dataset._get_data()
    assert isinstance(res, tuple), (
        "Output of get_data should be a 2-tuple"
    )
    assert len(res) == 2, (
        "Output of get_data should be a 2-tuple"
    )

    dimension, data = res

    assert isinstance(dimension, tuple), (
        "First output of get_data should be an integer or a tuple of integers."
        f" Got {dimension}."
    )
    assert all(isinstance(d, numbers.Integral) for d in dimension), (
        "First output of get_data should be an integer or a tuple of integers."
        f" Got {dimension}."
    )
    assert isinstance(data, dict), (
        f"Second output of get_data should be a dict. Got {data}."
    )


def test_solver_class(benchmark, solver_class):
    """Check that all installed solver_class respects the public API"""

    # Check that the solver_class exposes a name
    assert hasattr(solver_class, 'name'), "All solver should expose a name"
    assert isinstance(solver_class.name, str), (
        "The solver's name should be a string"
    )

    # Check that the solver_class uses a valid stop_strategy
    assert solver_class.stop_strategy in STOP_STRATEGIES


def test_solver_install_api(benchmark, solver_class):

    # Check that the solver_class exposes a known install cmd
    assert solver_class.install_cmd in [None, 'conda', 'shell']

    # Check that the solver_class exposes a known install cmd
    if solver_class.install_cmd == 'conda':
        assert hasattr(solver_class, 'requirements')
    if solver_class.install_cmd == 'shell':
        assert hasattr(solver_class, 'install_script')


@pytest.mark.requires_install
def test_solver_install(test_env_name, benchmark, solver_class, xfail_check):

    if xfail_check is not None:
        xfail_check(solver_class)

    # assert that install works when forced to reinstalls
    solver_class.install(env_name=test_env_name)
    solver_class.is_installed(
        env_name=test_env_name, raise_on_not_installed=True
    )


def test_solver(benchmark, solver_class):

    if not solver_class.is_installed():
        pytest.skip("Solver is not installed")

    # Skip test_solver for julia in OSX as it throw a segfault
    # See issue#64
    if 'julia' in solver_class.name.lower() and sys.platform == 'darwin':
        pytest.skip('Julia causes segfault on OSX for now.')

    objective_class = benchmark.get_benchmark_objective()
    objective = objective_class.get_instance()

    datasets = benchmark.list_benchmark_datasets()
    simulated_dataset = [d for d in datasets if d.name.lower() == 'simulated']

    assert len(simulated_dataset) == 1, (
        "All benchmark need to implement a simulated dataset for "
        "testing purpose"
    )

    dataset_class = simulated_dataset[0]
    dataset = dataset_class.get_instance()

    dimension, data = dataset._get_data()
    objective.set_data(**data)

    solver = solver_class.get_instance()
    solver.set_objective(**objective.to_dict())

    # Either call run_with_cb or run
    if solver.stop_strategy == 'callback':
        sc = StoppingCriterion._get_instance(max_runs=25, timeout=None)
        cb = _Callback(
            objective, meta={}, stopping_criterion=sc
        )
        solver.run(cb)
    else:
        stop_val = 5000 if solver_class.stop_strategy == 'iteration' else 1e-15
        solver.run(stop_val)

    beta_hat_i = solver.get_result()

    assert beta_hat_i.shape == dimension

    val_star = objective(beta_hat_i)['objective_value']
    for _ in range(100):
        eps = 1e-5 * np.random.randn(*dimension)
        val_eps = objective(beta_hat_i + eps)['objective_value']
        diff = val_eps - val_star
        assert diff > 0
