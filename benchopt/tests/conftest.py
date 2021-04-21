import os
import uuid
import pytest

from benchopt.benchmark import Benchmark
from benchopt.utils.conda_env_cmd import create_conda_env
from benchopt.utils.conda_env_cmd import delete_conda_env
from benchopt.utils.dynamic_modules import _get_module_from_file

from benchopt.tests import TEST_BENCHMARK_DIR

os.environ['BENCHOPT_DEBUG'] = '1'
os.environ['BENCHOPT_RAISE_INSTALL_ERROR'] = '1'

_TEST_ENV_NAME = None
_EMPTY_ENV_NAME = None


def class_ids(p):
    if hasattr(p, 'name'):
        return p.name.lower()
    return str(p)


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
        ('benchmark', 'dataset_simu'): lambda benchmarks: [
            (benchmark, dataset_class) for benchmark in benchmarks
            for dataset_class in benchmark.list_benchmark_datasets()
            if dataset_class.name.lower() == 'simulated'
        ],
        ('benchmark', 'dataset_class'): lambda benchmarks: [
            (benchmark, dataset_class) for benchmark in benchmarks
            for dataset_class in benchmark.list_benchmark_datasets()
        ],
        ('benchmark', 'solver_class'): lambda benchmarks: [
            (benchmark, solver) for benchmark in benchmarks
            for solver in benchmark.list_benchmark_solvers()
        ]
    }

    # Get all benchmarks
    benchmarks = metafunc.config.getoption("benchmark")
    if benchmarks is None or len(benchmarks) == 0:
        benchmarks = TEST_BENCHMARK_DIR.glob('*/')
    benchmarks = [Benchmark(b) for b in benchmarks]
    benchmarks.sort()

    # Parametrize the tests
    for params, func in PARAMETRIZATION.items():
        if set(params).issubset(metafunc.fixturenames):
            metafunc.parametrize(params, func(benchmarks), ids=class_ids)


@pytest.fixture
def xfail_check(request):

    if 'benchmark' not in request.fixturenames:
        raise ValueError(
            '`xfail_check` fixture should only be used in tests parametrized '
            'with `benchmark` fixture'
        )

    benchmark = request.getfixturevalue('benchmark')
    xfail_file = benchmark.get_xfail_file()
    if xfail_file is None:
        return None
    xfail_module = _get_module_from_file(xfail_file)
    xfail_func_name = f"xfail_{request.function.__name__}"
    return getattr(xfail_module, xfail_func_name, None)


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


@pytest.fixture(scope='session')
def empty_env_name(request):
    global _EMPTY_ENV_NAME

    if _EMPTY_ENV_NAME is None:
        env_name = f"_benchopt_test_env_{uuid.uuid4()}"
        request.addfinalizer(delete_empty_env)

        _EMPTY_ENV_NAME = env_name

        create_conda_env(_EMPTY_ENV_NAME, empty=True)

    return _EMPTY_ENV_NAME


def delete_test_env():
    global _TEST_ENV_NAME

    if _TEST_ENV_NAME is not None:
        delete_conda_env(_TEST_ENV_NAME)
        _TEST_ENV_NAME = None


def delete_empty_env():
    global _EMPTY_ENV_NAME

    if _EMPTY_ENV_NAME is not None:
        delete_conda_env(_EMPTY_ENV_NAME)
        _EMPTY_ENV_NAME = None
