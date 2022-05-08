import pytest
import numbers
import inspect

import numpy as np

from benchopt.runner import _Callback
from benchopt.stopping_criterion import STOPPING_STRATEGIES
from benchopt.utils import product_param


def test_benchmark_objective(benchmark, dataset_simu):
    """Check that the objective function and the datasets are well defined."""
    objective_class = benchmark.get_benchmark_objective()
    objective = objective_class.get_instance()

    dataset = dataset_simu.get_instance()
    objective.set_dataset(dataset)

    # check that the reported dimension is correct and that the result of
    # the objective function is a dictionary containing a scalar value for
    # `objective_value`.
    beta_hat = objective.get_one_solution()
    objective_dict = objective(beta_hat)

    assert 'objective_value' in objective_dict, (
        "When the output of objective is a dict, it should at least "
        "contain a value associated to `objective_value` which will be "
        "used to detect the convergence of the algorithm."
    )
    assert np.isscalar(objective_dict['objective_value']), (
        "The output of the objective function should be a scalar, or a "
        "dict containing a scalar associated to `objective_value`."
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

    data = dataset._get_data()
    assert isinstance(data, (tuple, dict)), (
        "Output of get_data should be a 2-tuple or a dict."
    )
    # XXX - Remove in version 1.3
    if isinstance(data, tuple):
        assert len(data) == 2, (
            "Output of get_data should be a 2-tuple"
        )

        dimension, data = data

        assert isinstance(dimension, tuple) or dimension == 'object', (
            "First output of get_data should be an integer or a tuple of "
            f"integers. Got {dimension}."
        )
        if dimension != 'object':
            assert all(isinstance(d, numbers.Integral) for d in dimension), (
                "First output of get_data should be an integer or a tuple of "
                f"integers. Got {dimension}."
            )

    assert isinstance(data, dict), (
        f"The returned data from get_data should be a dict. Got {data}."
    )


def test_solver_class(benchmark, solver_class):
    """Check that all installed solver_class respects the public API"""

    # Check that the solver_class exposes a name
    assert hasattr(solver_class, 'name'), "All solver should expose a name"
    assert isinstance(solver_class.name, str), (
        "The solver's name should be a string"
    )

    # Check that the solver_class uses a valid stopping_strategy
    if hasattr(solver_class, 'stopping_strategy'):
        msg = f"stopping_strategy should be in {STOPPING_STRATEGIES}."
        assert solver_class.stopping_strategy in STOPPING_STRATEGIES, msg

    # Check that the solver_class uses a valid callable to override get_next.
    if hasattr(solver_class, 'get_next'):
        is_static = isinstance(
            inspect.getattr_static(solver_class, "get_next"),
            staticmethod
        )
        assert (callable(solver_class.get_next) and is_static), (
            "`get_next` for class Solver in "
            f"'{solver_class.__module__}' should be a callable static method."
        )
        # Make sure the signature is def get_next(int):
        solver_class.get_next(0)


def test_solver_install_api(benchmark, solver_class):

    # Check that the solver_class exposes a known install cmd
    assert solver_class.install_cmd in [None, 'conda', 'shell']

    # Check that the solver_class exposes a known install cmd
    if solver_class.install_cmd == 'conda':
        assert hasattr(solver_class, 'requirements')
    if solver_class.install_cmd == 'shell':
        assert hasattr(solver_class, 'install_script')


@pytest.mark.requires_install
def test_solver_install(test_env_name, benchmark, solver_class, check_test):

    if check_test is not None:
        check_test(solver_class)

    # assert that install works when forced to reinstalls
    solver_class.install(env_name=test_env_name)
    solver_class.is_installed(
        env_name=test_env_name, raise_on_not_installed=True
    )


def test_solver(benchmark, solver_class):

    # Check that a solver run with at least one configuration of a simulated
    # dataset.

    if not solver_class.is_installed():
        pytest.skip("Solver is not installed")

    objective_class = benchmark.get_benchmark_objective()
    objective = objective_class.get_instance()

    simulated_dataset = [
        d for d in benchmark.get_datasets() if d.name.lower() == 'simulated'
    ]

    assert len(simulated_dataset) == 1, (
        "All benchmark need to implement a simulated dataset for "
        "testing purpose. The dataset should have `name='simulated'."
    )

    dataset_class = simulated_dataset[0]
    test_parameters = product_param(getattr(
        dataset_class,
        'test_parameters',
        {},
    ))
    if not test_parameters:
        test_parameters = [{}]
    solver_ran_once = False
    for test_params in test_parameters:
        dataset = dataset_class.get_instance(**test_params)

        objective.set_dataset(dataset)

        solver = solver_class.get_instance()
        skip, reason = solver._set_objective(objective)
        if skip:
            continue
        solver_ran_once = True
        _test_solver_one_objective(solver, objective)

    assert solver_ran_once, (
        'Solver skipped all simulated dataset configs. At least one simulated '
        'dataset config should be compatible with a solver'
    )


def _test_solver_one_objective(solver, objective):
    # Test a solver runs with a given objective and give proper result.

    is_convex = getattr(objective, "is_convex", True)

    # Either call run_with_cb or run
    if solver._solver_strategy == 'callback':
        sc = solver.stopping_criterion.get_runner_instance(
            max_runs=25 if is_convex else 2, timeout=None, solver=solver
        )
        if not is_convex:
            # Set large tolerance for the stopping criterion to stop fast
            sc.eps = 5e-1
        cb = _Callback(
            objective, meta={}, stopping_criterion=sc
        )
        solver.run(cb)
    else:
        if solver._solver_strategy == 'iteration':
            stop_val = 5000 if is_convex else 2
        else:
            stop_val = 1e-15 if is_convex else 1e-2
        solver.run(stop_val)

    # Check that beta_hat is compatible to compute the objective function
    beta_hat = solver.get_result()
    objective(beta_hat)

    if is_convex:
        val_star = objective(beta_hat)['objective_value']
        for _ in range(100):
            eps = 1e-5 * np.random.randn(*beta_hat.shape)
            val_eps = objective(beta_hat + eps)['objective_value']
            diff = val_eps - val_star
            assert diff >= 0
