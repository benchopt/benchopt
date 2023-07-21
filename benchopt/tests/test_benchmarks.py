import pytest
import numpy as np

import benchopt
from benchopt.cli.main import run
from benchopt.runner import _Callback
from benchopt.stopping_criterion import SAMPLING_STRATEGIES
from benchopt.utils import product_param
from benchopt.utils.temp_benchmark import temp_benchmark


def test_benchmark_objective(benchmark, dataset_simu):
    """Check that the objective function and the datasets are well defined."""
    objective_class = benchmark.get_benchmark_objective()
    objective = objective_class.get_instance()

    dataset = dataset_simu.get_instance()
    objective.set_dataset(dataset)

    # check that the reported dimension is correct and that the result of
    # the objective function is a dictionary containing a scalar value for
    # `objective_value`.
    beta_hat = objective.get_one_result()
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

    # XXX TODO remove when scikit-learn releases the fix
    # see https://github.com/scikit-learn/scikit-learn/pull/23358
    if dataset_class.name.lower() == 'leukemia':
        pytest.skip("Leukemia download is broken in scikit-learn 1.1.0")

    data = dataset._get_data()
    assert isinstance(data, (tuple, dict)), (
        "Output of get_data should be a 2-tuple or a dict."
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
        msg = f"stopping_strategy should be in {SAMPLING_STRATEGIES}."
        assert solver_class.stopping_strategy in SAMPLING_STRATEGIES, msg

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

    test_config = getattr(solver_class, "test_config", {})
    objective_config = test_config.get('objective', {})
    dataset_config = test_config.get('dataset', {})

    objective_class = benchmark.get_benchmark_objective()
    objective = objective_class.get_instance(**objective_config)

    simulated_dataset = [
        d for d in benchmark.get_datasets() if d.name.lower() == 'simulated'
    ]

    assert len(simulated_dataset) == 1, (
        "All benchmark need to implement a simulated dataset for "
        "testing purpose. The dataset should have `name='simulated'."
    )

    dataset_class = simulated_dataset[0]
    dataset_test_parameters = product_param(getattr(
        dataset_class, 'test_parameters', {}
    ))
    if not dataset_test_parameters:
        dataset_test_parameters = [{}]
    solver_ran_once = False
    for params in dataset_test_parameters:
        params.update(dataset_config)
        dataset = dataset_class.get_instance(**params)

        objective.set_dataset(dataset)
        solver = solver_class.get_instance()
        skip = solver._set_objective(objective)
        if skip:
            continue
        solver_ran_once = True
        _test_solver_one_objective(solver, objective)

    assert solver_ran_once, (
        'Solver skipped all test configuration. At least one simulated '
        'dataset and one objective config should be compatible with the '
        'solver, potentially provided through "Solver.test_config" class '
        'attribute or with `Dataset.test_parameters`.'
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
        cb.start()
        solver.run(cb)
    else:
        if solver._solver_strategy == 'iteration':
            stop_val = 5000 if is_convex else 2
        else:
            stop_val = 1e-10 if is_convex else 1e-2
        solver.run(stop_val)

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


def test_deprecated_stopping_strategy():
    # XXX remove in 1.5
    assert benchopt.__version__ < '1.5'

    solver1 = """from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = 'solver1'
        stopping_strategy = 'iteration'

        def run(self, n_iter): pass

        def set_objective(self, X, y, lmbd):
            self.n_features = X.shape[1]

        def get_result(self, **data):
            return {'beta': np.zeros(self.n_features)}
    """

    solver2 = solver1.replace("stopping_strategy", "sampling_strategy")
    solver2 = solver2.replace("solver1", "solver2")

    with temp_benchmark(solvers=[solver1, solver2]) as benchmark:
        with pytest.warns(
                FutureWarning,
                match="'stopping_strategy' attribute is deprecated"):
            run([str(benchmark.benchmark_dir),
                 *'-s solver1 -d test-dataset -n 1 -r 1 --no-plot'.split()],
                standalone_mode=False)

        run([str(benchmark.benchmark_dir),
             *'-s solver2 -d test-dataset -n 1 -r 1 --no-plot'.split()],
            standalone_mode=False)


def test_deprecated_support_sparse():
    # XXX remove in 1.5
    assert benchopt.__version__ < '1.5'

    solver1 = """from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = 'solver1'
        support_sparse = True

        def run(self, n_iter): pass

        def set_objective(self, X, y, lmbd):
            self.n_features = X.shape[1]

        def get_result(self, **data):
            return np.zeros(self.n_features)
    """

    with temp_benchmark(solvers=solver1) as benchmark:
        with pytest.warns(
                FutureWarning,
                match="`support_sparse = False` is deprecated"):
            run([str(benchmark.benchmark_dir),
                 *'-s solver1 -d test-dataset -n 1 -r 1 --no-plot'.split()],
                standalone_mode=False)
