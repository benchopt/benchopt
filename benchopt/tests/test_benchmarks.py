import pytest
import numpy as np

from benchopt.base import SAMPLING_STRATEGIES

from benchopt.util import get_all_benchmarks
from benchopt.util import get_benchmark_objective
from benchopt.util import list_benchmark_solvers
from benchopt.util import list_benchmark_datasets
from benchopt.util import check_failed_import
from benchopt.util import create_condaenv, delete_condaenv


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


# Setup and clean a test env to install/uninstall all the solvers and check
# that they are correctly configured

TEST_ENV_NAME = "benchopt_test_env"


def setup_module(module):
    print("create env")
    create_condaenv(TEST_ENV_NAME, recreate=True)


def teardown_module(module):
    delete_condaenv(TEST_ENV_NAME)


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
    if dataset_class.install_cmd == 'conda':
        for package in dataset_class.requirements_import:
            pytest.importorskip(package)

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
    assert solver_class.install_cmd in [None, 'conda', 'bash']

    # Check that the solver_class exposes a known install cmd
    if solver_class.install_cmd == 'conda':
        assert hasattr(solver_class, 'requirements')
    if solver_class.install_cmd == 'bash':
        assert hasattr(solver_class, 'install_script')
        assert hasattr(solver_class, 'cmd_name')


@pytest.mark.requires_install
@pytest.mark.parametrize('benchmark_name, solver_class', BENCH_AND_SOLVERS,
                         ids=class_ids)
def test_solver_install(benchmark_name, solver_class):
    if solver_class.name in ['Liblinear', 'Cyanure']:
        pytest.xfail('%s is not fully working yet' % solver_class.name)

    # assert that install works in a fresh environment
    create_condaenv(TEST_ENV_NAME, recreate=True)
    assert solver_class.install(env_name=TEST_ENV_NAME, force=True)
    assert solver_class.is_installed(env_name=TEST_ENV_NAME)

    # if solver_class.install_cmd == 'conda':
    #     # solver_class.uninstall(env_name=TEST_ENV_NAME)
    #     assert not solver_class.is_installed(env_name=TEST_ENV_NAME)


@pytest.mark.parametrize('benchmark_name, solver_class', BENCH_AND_SOLVERS,
                         ids=class_ids)
def test_solver(benchmark_name, solver_class):

    if solver_class.install_cmd == 'conda':
        for package in solver_class.requirements_import:
            pytest.importorskip(package)
    elif not solver_class.is_installed():
        pytest.skip("Solver is not installed")

    if check_failed_import(solver_class):
        pytest.skip("Solver import failed")

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
        eps = 1e-9 * np.random.randn(scale)
        val_eps = objective(beta_hat_i + eps)
        diff = val_eps - val_star
        assert diff > 0


if __name__ == "__main__":
    # create_condaenv(TEST_ENV_NAME, recreate=True)
    for idx in range(8):
        if idx == 5:  # cyanure, skip
            continue
        bench, solver_class = BENCH_AND_SOLVERS[idx]
        print(bench, solver_class)
        create_condaenv(TEST_ENV_NAME, recreate=True)
        assert solver_class.install(env_name=TEST_ENV_NAME, force=True)
        assert solver_class.is_installed(env_name=TEST_ENV_NAME)

        # if solver_class.install_cmd == 'conda':
        #     # solver_class.uninstall(env_name=TEST_ENV_NAME)
        #     assert not solver_class.is_installed(env_name=TEST_ENV_NAME)
