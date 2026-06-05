import os
import sys
import uuid
import pytest
import shutil
from collections import defaultdict

from benchopt.benchmark import Benchmark
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.utils.conda_env_cmd import create_conda_env
from benchopt.utils.conda_env_cmd import delete_conda_env
from benchopt.utils.shell_cmd import _run_shell_in_conda_env
from benchopt.utils.env_management import UvBackend

os.environ['BENCHOPT_DEBUG'] = '1'
os.environ['BENCHOPT_RAISE_INSTALL_ERROR'] = '1'
os.environ['BENCHOPT_WARN_NONUNIQUE_FILES'] = '0'

_TEST_ENV_NAME = None
_EMPTY_ENV_NAME = None
_TEST_UV_ENV_PATH = None
_TEST_BENCHMARK = None

# Track ``test_solver_run`` outcomes per solver to check that at least one
# config runs for each solver.
_SOLVER_RUN_OUTCOMES = defaultdict(list)


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
    parser.addoption("--test-uv-env", type=str, default=None,
                     help="Use a given uv venv (path or bare name under the "
                          "uv envs dir) to test the uv backend.")
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


@pytest.fixture(scope='session')
def benchmark():
    return _TEST_BENCHMARK


@pytest.fixture
def require_solver_installed(solver_class):
    # Skips a test if the solver class is not installed.
    if not solver_class.is_installed():
        pytest.skip("Solver is not installed")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--skip-install"):
        return
    skip_install = pytest.mark.skip(reason="Skipping installs in this run")
    for item in items:
        if "requires_install" in item.keywords:
            item.add_marker(skip_install)


def _get_skip_reason(report):
    if not report.skipped:
        return ""
    if isinstance(report.longrepr, tuple) and len(report.longrepr) >= 3:
        return str(report.longrepr[2])
    return ""


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # Collect the outcomes for all test_solver_run for each solver,
    # to check that at least one configuration runs for each solver.
    outcome = yield
    if item.originalname != 'test_solver_run':
        return

    report = outcome.get_result()
    # Only record call-phase outcomes — setup-phase skips come from markers
    # or fixture opt-outs, which are not coverage gaps.
    if report.when == 'call':
        reason = _get_skip_reason(report)
        solver = item.funcargs.get('solver_class')
        dataset_name = item.funcargs.get('test_dataset_name')
        _SOLVER_RUN_OUTCOMES[solver.name].append(
            (report.outcome, dataset_name, reason)
        )


def pytest_sessionfinish(session, exitstatus):
    # Check which solvers were flag for being skipped for all configuration
    flagged = sorted(
        (solver, sorted({tuple(r) for _, *r in entries}))
        for solver, entries in _SOLVER_RUN_OUTCOMES.items()
        if entries and all(o == 'skipped' for o, *_ in entries)
    )
    if not flagged:
        return

    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is None:
        return

    # Synthesize a failed TestReport for each flagged solver
    from _pytest.reports import TestReport
    template = next(
        (i for i in session.items if i.originalname == 'test_solver_run'),
        None,
    )
    nodeid_base = template.nodeid.split('[', 1)[0]
    fspath = template.location[0]
    for solver, reasons in flagged:
        name = f"test_solver_run[{solver}]"
        skipped_datasets = "\n- ".join(
            f"{dataset} (reason: {reason})"
            for _, dataset, reason in _SOLVER_RUN_OUTCOMES[solver]
        )
        longrepr = (
            f"Skipped every test_solver_run variants for solver '{solver}'."
            "\nPlease ensure at least one configuration runs for each solver."
            f"\nTested datasets:\n- {skipped_datasets}\n\n"
            "To change the datasets tested for this solver, set:\n"
            "  Solver.test_config = {'dataset': {'name': '<dataset_name>'}}\n"
            "or, to test multiple datasets:\n"
            "  Solver.test_config = {'dataset': {'name': ['<a>', '<b>']}}\n"
            "You can also set this test parameters globally for the benchmark "
            "by setting them in the Objective instead of the Solver."
        )
        report = TestReport(
            nodeid=f"{nodeid_base}[{solver}]",
            location=(fspath, 0, name),
            keywords={},
            outcome='failed',
            longrepr=longrepr,
            when='call',
        )
        reporter.stats.setdefault('failed', []).append(report)
    session.exitstatus = 1


def pytest_generate_tests(metafunc):
    """Generate the test on the fly to take --benchmark into account."""
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

    parametrization = {
        'dataset_class': benchmark.get_datasets(),
        'solver_class': benchmark.get_solvers(),
    }

    needs_dataset_name = 'test_dataset_name' in metafunc.fixturenames
    parametrized = False

    for param, values in parametrization.items():
        if param not in metafunc.fixturenames:
            continue
        parametrized = True
        if needs_dataset_name:
            expanded = []
            for v in values:
                solver = v if param == 'solver_class' else None
                names = benchmark.get_test_dataset_names(solver_class=solver)
                if not names:
                    _raise_no_test_dataset(solver)
                expanded.extend((v, name) for name in names)
            metafunc.parametrize(
                (param, 'test_dataset_name'), expanded, ids=class_ids
            )
        else:
            metafunc.parametrize(param, values, ids=class_ids)

    # Tests that only request ``test_dataset_name`` (e.g. objective-level
    # checks) get expanded with the objective-level dataset names.
    if needs_dataset_name and not parametrized:
        names = benchmark.get_test_dataset_names()
        if not names:
            _raise_no_test_dataset(None)
        metafunc.parametrize(
            'test_dataset_name', names, ids=class_ids,
        )


def _raise_no_test_dataset(solver):
    target = (
        f"solver {solver.name!r}" if solver is not None
        else "the benchmark objective"
    )
    raise ValueError(
        f"No test_dataset_name configured for {target}. "
        "Set `Objective.test_dataset_name` (legacy), "
        "`Objective.test_config['dataset']['name']`, or "
        "`Solver.test_config['dataset']['name']` to one or more dataset "
        "names. Default to 'simulated' dataset if it exists."
    )


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


@pytest.fixture
def warn_override(request):
    """Deactivate the raise install error for a test."""
    os.environ["BENCHOPT_WARN_NONUNIQUE_FILES"] = "1"
    yield
    os.environ["BENCHOPT_WARN_NONUNIQUE_FILES"] = "0"


@pytest.fixture(scope='session')
def use_env(request):
    if request.config.getoption("--skip-env"):
        pytest.skip("Skip creating a test env")


@pytest.fixture(scope='session')
def test_env_name(request, benchmark, use_env):
    global _TEST_ENV_NAME

    if _TEST_ENV_NAME is None:
        if request.config.getoption("--skip-env"):
            pytest.skip("Skip creating a test env")
        if shutil.which("conda") is None:
            pytest.skip("conda is not installed on PATH")
        env_name = request.config.getoption("--test-env")
        recreate = request.config.getoption("--recreate")
        if env_name is None:
            env_name = f"_benchopt_test_env_{uuid.uuid4()}"
            request.addfinalizer(delete_test_env)

        _TEST_ENV_NAME = env_name

        benchmark.create_test_env(env_name, recreate=recreate)

        # Flush the output to avoid issues with pytest capturing
        # the output later on and failing tests because of it.
        # Make sure to flush stdout and stderr
        print(flush=True)
        print(flush=True, file=sys.stderr)

    return _TEST_ENV_NAME


@pytest.fixture(scope='session')
def empty_env_name(request, use_env):
    global _EMPTY_ENV_NAME

    if _EMPTY_ENV_NAME is None:
        if shutil.which("conda") is None:
            pytest.skip("conda is not installed on PATH")
        env_name = f"_benchopt_test_env_{uuid.uuid4()}"
        _EMPTY_ENV_NAME = env_name

        request.addfinalizer(delete_empty_env)
        create_conda_env(env_name, empty=True)

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


@pytest.fixture(scope='session')
def test_uv_env_path(request, bench, use_env):
    """Session-scoped uv venv with benchopt installed editable.

    Honors ``--test-uv-env`` to reuse an existing venv across pytest runs
    (in which case finalization does not delete it).
    """
    global _TEST_UV_ENV_PATH

    from benchopt.utils.env_management import (
        reset_active_backend, set_active_backend,
    )
    if _TEST_UV_ENV_PATH is None:
        if shutil.which("uv") is None:
            pytest.skip("uv is not installed on PATH")
        provided = request.config.getoption("--test-uv-env")
        if provided is None:
            env_name = f"_benchopt_test_uv_env_{uuid.uuid4()}"
            request.addfinalizer(delete_uv_test_env)
        else:
            env_name = provided
        _TEST_UV_ENV_PATH = env_name

        backend = UvBackend()
        backend.create_env(env_name, benchmark=bench, pytest=True)
        # The bench objective install must use the uv backend too,
        # otherwise the conda default would try to activate a uv venv.
        set_active_backend("uv")
        try:
            bench.get_benchmark_objective().install(env_name=env_name)
        finally:
            reset_active_backend()
        print(flush=True)
        print(flush=True, file=sys.stderr)

    return _TEST_UV_ENV_PATH


def delete_uv_test_env():
    global _TEST_UV_ENV_PATH

    if _TEST_UV_ENV_PATH is not None:
        UvBackend().delete_env(_TEST_UV_ENV_PATH)
        _TEST_UV_ENV_PATH = None


@pytest.fixture
def backend_test_env(request):
    """Yield ``(backend_name, env_name)`` for a parametrized test.

    Use as an indirect parametrize value: ``"conda"`` or ``"uv"``.
    """
    backend = request.param
    if backend == "conda":
        env_name = request.getfixturevalue("test_env_name")
    elif backend == "uv":
        env_name = request.getfixturevalue("test_uv_env_path")
    else:
        pytest.skip(f"unknown backend {backend!r}")
    from benchopt.utils.env_management import (
        reset_active_backend, set_active_backend,
    )
    set_active_backend(backend)
    yield backend, env_name
    reset_active_backend()


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
    cmd = "pip uninstall -qqy pytest"

    # Uninstall pytest in the test env to test the behavior when pytest is not
    # installed.
    _run_shell_in_conda_env(cmd, env_name=test_env_name)
    yield
    # reinstall pytest in the test_env
    exitcode, output = _run_shell_in_conda_env(
        "pip install -q pytest", env_name=test_env_name,
        return_output=True
    )
    assert exitcode == 0, output
