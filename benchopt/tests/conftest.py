import uuid
import pytest

from benchopt.benchmark import Benchmark
from benchopt.config import DEFAULT_GLOBAL
from benchopt.utils.shell_cmd import delete_conda_env
from benchopt.utils.shell_cmd import create_conda_env

from benchopt.tests import TEST_BENCHMARK_DIR


DEFAULT_GLOBAL['debug'] = True
DEFAULT_GLOBAL['raise_install_error'] = True

_TEST_ENV_NAME = None


def class_ids(parameters):
    name_id = ''
    for p in parameters:
        if hasattr(p, 'name'):
            p = p.name.lower()
        name_id = f'{name_id}-{p}'
    if name_id.startswith('-'):
        name_id = name_id[1:]
    return name_id


def pytest_report_header(config):
    return "project deps: mylib-1.1"


def pytest_addoption(parser):
    parser.addoption("--skip-install", action="store_true",
                     help="skip install of solvers that can slow down CI.")
    parser.addoption("--test-env", type=str, default=None,
                     help="Use a given env to test the solvers' install.")
    parser.addoption("--recreate", action="store_true",
                     help="Recreate the environment if it already exists.")
    parser.addoption("--benchmark", type=str, default=None, nargs='*',
                     help="Specify a benchmark to test.")


def pytest_configure(config):
    """Setup pytest for benchopt testing"""

    config.addinivalue_line("markers", "requires_install")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--skip-install"):
        return

    skip_install = pytest.mark.skip(
            reason="--skip-install option provided")
    for item in items:
        if "requires_install" in item.keywords:
            item.add_marker(skip_install)


def pytest_generate_tests(metafunc):
    """Generate the test on the fly to take --benchmark into account.
    """
    PARAMETRIZATION = {
        'benchmark_dataset_simu': lambda benchmarks: [
            (benchmark, dataset_class) for benchmark in benchmarks
            for dataset_class in benchmark.list_benchmark_datasets()
            if dataset_class.name.lower() == 'simulated'
        ],
        'benchmark_dataset': lambda benchmarks: [
            (benchmark, dataset_class) for benchmark in benchmarks
            for dataset_class in benchmark.list_benchmark_datasets()
        ],
        'benchmark_solver': lambda benchmarks: [
            (benchmark, solver) for benchmark in benchmarks
            for solver in benchmark.list_benchmark_solvers()
        ]
    }
    for params, func in PARAMETRIZATION.items():
        if params in metafunc.fixturenames:
            benchmarks = metafunc.config.getoption("benchmark")
            if benchmarks is None or len(benchmarks) == 0:
                benchmarks = TEST_BENCHMARK_DIR.glob('*/')
            benchmarks = [Benchmark(b) for b in benchmarks]
            benchmarks.sort()
            metafunc.parametrize(params, func(benchmarks), ids=class_ids)


@pytest.fixture(scope='session')
def test_env_name(request):
    global _TEST_ENV_NAME

    if _TEST_ENV_NAME is None:
        env_name = request.config.getoption("--test-env")
        recreate = request.config.getoption("--recreate")
        if env_name is None:
            env_name = f"_benchopt_test_env_{uuid.uuid4()}"
            request.addfinalizer(delete_test_env)

        _TEST_ENV_NAME = env_name

        create_conda_env(_TEST_ENV_NAME, recreate=recreate)

    return _TEST_ENV_NAME


def delete_test_env():
    global _TEST_ENV_NAME

    if _TEST_ENV_NAME is not None:
        delete_conda_env(_TEST_ENV_NAME)
