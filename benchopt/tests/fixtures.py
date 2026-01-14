import os
import uuid
import pytest

from benchopt.benchmark import Benchmark
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.utils.conda_env_cmd import create_conda_env
from benchopt.utils.conda_env_cmd import delete_conda_env
from benchopt.utils.shell_cmd import _run_shell_in_conda_env

os.environ['BENCHOPT_DEBUG'] = '1'
os.environ['BENCHOPT_RAISE_INSTALL_ERROR'] = '1'

_TEST_ENV_NAME = None
_EMPTY_ENV_NAME = None
_TEST_BENCHMARK = None


def class_ids(p):
    if hasattr(p, 'name'):
        return p.name.lower()
    return str(p)


def pytest_report_header(config):
    return "project deps: mylib-1.1"


def pytest_addoption(parser):
    parser.addoption("--skip-install", action="store_true",
                     help="skip install of solvers that can slow down CI.")
    parser.addoption("--skip-env", action="store_true",
                     help="skip tests which requires creating a conda env.")
    parser.addoption("--test-env", type=str, default=None,
                     help="Use a given env to test the solvers' install.")
    parser.addoption("--recreate", action="store_true",
                     help="Recreate the environment if it already exists.")
    parser.addoption("--benchmark", type=str, default=None,
                     help="Specify a benchmark to test.")


def pytest_configure(config):
    """Setup pytest for benchopt testing"""
    global _TEST_BENCHMARK

    import matplotlib
    matplotlib.use("Agg")

    config.addinivalue_line("markers", "requires_install")

    # Create the benchmark for which the tests are run. If it is not provided,
    # we use a temporary benchmark with a dummy dataset and solver.
    benchmark_path = config.getoption("benchmark")
    if benchmark_path is not None:
        _TEST_BENCHMARK = Benchmark(benchmark_path)
    else:
        ctx = temp_benchmark()
        _TEST_BENCHMARK = ctx.__enter__()
        config._ctx = ctx


def pytest_unconfigure(config):
    """Teardown the temporary benchmark if any."""
    if hasattr(config, "_ctx"):
        config._ctx.__exit__(None, None, None)
        del config._ctx


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

    benchmark = _TEST_BENCHMARK
    if benchmark is None:
        raise ValueError(
            "The benchmark on which to run the tests has not been configured. "
            "When not provided, a temporary benchmark should be used. Please "
            "report this issue on GitHub."
        )

    # Make sure the tested benchmark is installed (we can import the Objective)
    benchmark.get_benchmark_objective().is_installed(
        raise_on_not_installed=True
    )

    # Extract the value for the parametrizations
    parametrization = {
        'dataset_class': [
            (benchmark, dataset) for dataset in benchmark.get_datasets()
        ],
        'solver_class': [
            (benchmark, solver) for solver in benchmark.get_solvers()
        ],
        'objective_class': [
            (benchmark, benchmark.get_benchmark_objective())
        ]
    }

    # Parametrize the tests
    for param, values in parametrization.items():
        if param in metafunc.fixturenames:
            metafunc.parametrize(
                ('benchmark', param), values, ids=class_ids
            )
            break


@pytest.fixture
def no_debug_log(request):
    """Deactivate the debug logs for a test."""
    os.environ["BENCHOPT_DEBUG"] = "0"
    yield
    os.environ["BENCHOPT_DEBUG"] = "1"


@pytest.fixture
def no_raise_install(request):
    """Deactivate the raise install error for a test."""
    os.environ["BENCHOPT_RAISE_INSTALL_ERROR"] = "0"
    yield
    os.environ["BENCHOPT_RAISE_INSTALL_ERROR"] = "1"


@pytest.fixture(scope='session')
def test_env_name(request):
    global _TEST_ENV_NAME

    if _TEST_ENV_NAME is None:
        if request.config.getoption("--skip-env"):
            pytest.skip("Skip creating a test env")
        env_name = request.config.getoption("--test-env")
        recreate = request.config.getoption("--recreate")
        if env_name is None:
            env_name = f"_benchopt_test_env_{uuid.uuid4()}"
            request.addfinalizer(delete_test_env)

        _TEST_ENV_NAME = env_name

        create_conda_env(_TEST_ENV_NAME, recreate=recreate)

    return _TEST_ENV_NAME


@pytest.fixture(scope='function')
def uninstall_dummy_package(test_env_name):
    _run_shell_in_conda_env(
        "pip uninstall -qqy dummy_package", env_name=test_env_name
    )
    yield
    _run_shell_in_conda_env(
        "pip uninstall -qqy dummy_package", env_name=test_env_name
    )


@pytest.fixture(scope='function')
def no_pytest(test_env_name):
    cmd = "which pytest\npip uninstall -qqy pytest"

    exitcode = _run_shell_in_conda_env(cmd, env_name=test_env_name)
    yield
    # If pytest was not installed before, exit code is 1 so do not reinstall
    # otherwise, reinstall it
    if exitcode == 0:
        exitcode, output = _run_shell_in_conda_env(
            "pip install -q pytest", env_name=test_env_name,
            return_output=True
        )
        assert exitcode == 0, output


@pytest.fixture(scope='session')
def empty_env_name(request):
    global _EMPTY_ENV_NAME

    if _EMPTY_ENV_NAME is None:
        if request.config.getoption("--skip-env"):
            pytest.skip("Skip creating a test env")
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
