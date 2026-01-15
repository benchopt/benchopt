import pytest
import numpy as np

from benchopt.stopping_criterion import StoppingCriterion
from benchopt.stopping_criterion import SAMPLING_STRATEGIES
from benchopt.utils.dynamic_modules import _get_module_from_file


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

    data = dataset._get_data()
    assert isinstance(data, (tuple, dict)), (
        "Output of get_data should be a 2-tuple or a dict."
    )

    assert isinstance(data, dict), (
        f"The returned data from get_data should be a dict. Got {data}."
    )


def test_benchmark_objective(benchmark, objective_class):
    # check that the result of the objective function is compatible with
    # benchopt, does not contain `objective_name` and is not empty.
    objective = objective_class.get_instance()
    dataset_class, test_params = benchmark.get_test_dataset()
    dataset = dataset_class.get_instance(**test_params[0])

    # get one value for the objective, with the test_dataset
    objective.set_dataset(dataset)
    result = objective._get_one_result()
    objective_output = objective(result)

    # check that the output has proper type and is not empty
    assert isinstance(objective_output, list), (
        "The output of the objective function should be a list of dicts by "
        "design. Please report this issue on benchopt's GitHub."
    )
    objective_output = objective_output[0]
    assert isinstance(objective_output, dict), (
        "The output of the objective function should be a dict by design. "
        "Please report this issue on benchopt's GitHub."
    )
    assert "objective_name" not in objective_output, (
        "`name` is a reserved key in the objective output dict. "
        "Please remove it from the output of the objective function."
    )
    assert len(objective_output) > 0, (
        "The output of the objective function should not be an empty dict."
    )


def test_solver_class(benchmark, solver_class):
    """Check that all installed solver_class respects the public API"""

    # Check that the solver_class exposes a name
    assert hasattr(solver_class, 'name'), "All solver should expose a name"
    assert isinstance(solver_class.name, str), (
        "The solver's name should be a string"
    )

    # Check that the solver_class uses a valid sampling_strategy
    if solver_class.sampling_strategy is not None:
        msg = f"sampling_strategy should be in {SAMPLING_STRATEGIES}."
        assert solver_class.sampling_strategy in SAMPLING_STRATEGIES, msg

    # Check that the solver_class uses a valid stopping criterion
    if hasattr(solver_class, 'stopping_criterion'):
        assert isinstance(solver_class.stopping_criterion, StoppingCriterion), (  # noqa E501
            "stopping_criterion should be an instance of StoppingCriterion. "
            f"Got '{solver_class.stopping_criterion}'"
        )

    # Check that the solver_class uses a valid callable to override get_next.
    if hasattr(solver_class, 'get_next'):
        assert callable(solver_class.get_next), (
            "`get_next` for class Solver in "
            f"'{solver_class.__module__}' should be a callable."
        )
        # Make sure the signature is def get_next(self, int). Create instance
        # of `solver_class` then call `get_next` since it is a class method
        solver_class().get_next(0)


def test_solver_install_api(benchmark, solver_class):

    # Check that the solver_class exposes a known install cmd
    assert solver_class.install_cmd in [None, 'conda', 'shell']

    # Check that the solver_class exposes a known install cmd
    if solver_class.install_cmd == 'shell':
        assert hasattr(solver_class, 'install_script')


@pytest.mark.requires_install
def test_solver_install(test_env_name, benchmark, solver_class):

    # Make sure that the current benchmark is correctly set
    from benchopt.benchmark import Benchmark
    benchmark = Benchmark(benchmark.benchmark_dir)

    # assert that install works when forced to reinstalls
    solver_class.install(env_name=test_env_name)
    solver_class.is_installed(
        env_name=test_env_name, raise_on_not_installed=True
    )


def test_solver_stopping_criterion(benchmark, solver_class):
    # Check each solver stopping_criterion is compatible with the objective
    objective_class = benchmark.get_benchmark_objective()
    objective = objective_class.get_instance()

    dataset_class, test_params = benchmark.get_test_dataset()
    dataset = dataset_class.get_instance(**test_params[0])

    # Make sure to inherit the objective if the stopping criterion
    # is set globally for this benchmark
    solver_class._inherit_stopping_criterion(objective)
    stopping_criterion = solver_class._stopping_criterion

    # check that stopping_criterion has the proper type
    assert isinstance(stopping_criterion, StoppingCriterion), (
        "The solver's stopping_criterion should be an instance of "
        "StoppingCriterion."
    )

    # Check that if a key_to_monitor is specified, the objective returns it
    if stopping_criterion.key_to_monitor is not None:
        key = stopping_criterion.key_to_monitor_
        assert key.startswith('objective_'), (
            "The solver's stopping_criterion key_to_monitor should start with "
            "'objective_'."
        )

        objective.set_dataset(dataset)
        result = objective._get_one_result()
        objective_output = objective(result)[0]

        requested_key = stopping_criterion.key_to_monitor
        available_keys = list(objective_output.keys())
        if not requested_key.startswith('objective_'):
            available_keys = [
                k.replace('objective_', '') for k in available_keys
            ]
        assert key in objective_output, (
            f"The solver's stopping_criterion monitors {requested_key}, but "
            "the objective does not return this key. Available keys are "
            f"{available_keys}."
        )


def test_solver_run(benchmark, solver_class):
    # Check that a solver run with at least one configuration of a simulated
    # dataset.

    if not solver_class.is_installed():
        pytest.skip("Solver is not installed")

    test_config = getattr(solver_class, "test_config", {})
    objective_config = test_config.get('objective', {})
    dataset_config = test_config.get('dataset', {})

    objective_class = benchmark.get_benchmark_objective()
    objective = objective_class.get_instance(**objective_config)

    dataset_class, test_params = benchmark.get_test_dataset()

    reasons = set()
    solver_ran_once = False
    for params in test_params:
        params.update(dataset_config)
        dataset = dataset_class.get_instance(**params)

        objective.set_dataset(dataset)
        solver = solver_class.get_instance(**test_config.get('solver', {}))
        skip, reason = solver._set_objective(objective)
        if skip:
            reasons.add(reason)
            continue
        solver_ran_once = True
        _test_solver_one_objective(solver, objective)

    reasons = "\n-".join(sorted(reasons))
    assert solver_ran_once, (
        'Solver skipped all test configuration. At least one simulated '
        'dataset and one objective config should be compatible with the '
        'solver, potentially provided through "Solver.test_config" class '
        f'attribute or with `Dataset.test_parameters`. Reasons:\n-{reasons}'
    )


def _test_solver_one_objective(solver, objective):
    # Test a solver runs with a given objective and give proper result.

    is_convex = getattr(objective, "is_convex", False)

    if solver._solver_strategy in ['iteration', 'callback']:
        stop_val = 5000 if is_convex else 2
    else:
        stop_val = 1e-10 if is_convex else 1e-2
    solver.run_once(stop_val)

    # Check that returned results are compatible with the objective
    result = solver.get_result()
    objective(result)

    # Only check optimality or convex problems, when solver only return
    # one value, which is a np.array
    if (is_convex and len(result) == 1
            and isinstance(list(result.values())[0], np.ndarray)):
        key = list(result.keys())[0]
        arr = result[key]
        val_star = objective(result)['objective_value']
        for _ in range(100):
            eps = 1e-5 * np.random.randn(*arr.shape)
            val_eps = objective({key: arr + eps})['objective_value']

            diff = val_eps - val_star
            assert diff >= 0


##############################################################################
# --- Utilities to test the CLI commands ----------------------------------- #
##############################################################################


@pytest.fixture(autouse=True)
def check_test(request):

    if 'benchmark' not in request.fixturenames:
        raise ValueError(
            '`check_test` fixture should only be used in tests parametrized '
            'with `benchmark` fixture'
        )

    benchmark = request.getfixturevalue('benchmark')
    test_config_file = benchmark.get_test_config_file()
    if test_config_file is None:
        return None
    test_config_module = _get_module_from_file(test_config_file)
    check_func_name = f"check_{request.function.__name__}"
    check_func = getattr(test_config_module, check_func_name, None)
    if check_func is None and request.function.__name__ == "test_solver_run":
        # Backward compatibility for benchmarks before benchopt 1.7.1
        check_func = getattr(test_config_module, "check_test_solver", None)
        if check_func is not None:
            warn_msg = (
                "The function `check_test_solver` is deprecated since "
                "benchopt 1.7.1. Please rename it to `check_test_solver_run`."
            )
            pytest.warns(DeprecationWarning, match=warn_msg)
    if check_func is not None:
        try:
            check_func(
                benchmark,
                *[
                    request.getfixturevalue(f) for f in request.fixturenames
                    if f not in [
                        'check_test', 'benchmark', 'request', 'test_env_name'
                    ]
                ]
            )
        except TypeError:
            # Backward compatibility for benchmarks before benchopt 1.7.1
            check_func(request.getfixturevalue('solver_class'))
