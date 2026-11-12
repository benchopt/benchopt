import pytest
from packaging.version import Version

import benchopt
from benchopt.cli.main import run
from benchopt.tests.utils import CaptureCmdOutput
from benchopt.utils.conda_env_cmd import get_env_file_from_requirements
from benchopt.utils.temp_benchmark import temp_benchmark


##############################################################################
# Deprecation check for benchopt 2.0
# XXX: remove in benchopt 2.0


def test_deprecated_channel_spec():
    with pytest.warns(DeprecationWarning):
        env = get_env_file_from_requirements(["chan:pkg"])
    assert env == (
        "channels:\n  - chan\n  - conda-forge\ndependencies:\n  - pkg"
    )

    with pytest.warns(DeprecationWarning):
        env = get_env_file_from_requirements(["pip:pkg"])
    assert env == "dependencies:\n  - pip\n  - pip:\n    - pkg"

    with pytest.warns(DeprecationWarning):
        env = get_env_file_from_requirements(["pip:git+https://test.org"])
    assert env == (
        "dependencies:\n  - pip\n  - pip:\n    - git+https://test.org"
    )

    with pytest.warns(DeprecationWarning):
        env = get_env_file_from_requirements(["pkg1", "chan:pkg2", "pip:pkg3"])
    assert env == (
        "channels:\n  - chan\n  - conda-forge\n"
        "dependencies:\n  - pkg1\n  - pkg2\n  - pip\n  - pip:\n    - pkg3"
    )


def test_deprecated_download_flag():
    """--download is a deprecated alias of --prepare."""
    with temp_benchmark() as bench:
        datasets = [(d, {}) for d in bench.get_datasets()]
        with pytest.warns(DeprecationWarning, match="--download.*deprecated"):
            bench.install_all_requirements(
                include_solvers=[],
                include_datasets=datasets,
                download=True,
                env_need_confirm=False,
            )


##############################################################################
# Deprecation check for benchopt 1.12
# XXX: remove in benchopt 1.12


def test_skip_api_removed():
    # Fails on the release that should drop the deprecated skip API.
    assert Version(benchopt.__version__) < Version("1.12"), (
        "Remove the deprecated skip API: `skip` receiving the data and "
        "returning a `(skip, reason)` tuple."
    )


@pytest.mark.parametrize('n_jobs', [1, 2])
def test_legacy_skip_signature(n_jobs):
    # `skip` receiving the data as kwargs still runs in the worker.
    objective = """from benchopt.utils.temp_benchmark import TempObjective

        class Objective(TempObjective):
            name = "Objective-skip"
            parameters = dict(should_skip=[True, False])
            def skip(self, X, y):
                if self.should_skip:
                    return True, "Objective#SKIP"
                return False, None
    """
    solver = """from benchopt.utils.temp_benchmark import TempSolver

        class Solver(TempSolver):
            name = "test-solver"
            sampling_strategy = 'run_once'
            parameters = dict(should_skip=[True, False])
            def run(self, n_iter): print("Solver#RUN")
            def skip(self, **obj):
                if self.should_skip:
                    return True, "Solver#SKIP"
                return False, None
    """
    with temp_benchmark(objective=objective, solvers=[solver]) as benchmark:
        with CaptureCmdOutput() as out:
            run([*(
                f'{benchmark.benchmark_dir} -s test-solver -d test-dataset '
                f'-j {n_jobs} --no-plot'
            ).split()], standalone_mode=False)

            from joblib.externals.loky import get_reusable_executor
            get_reusable_executor().shutdown(wait=True)

    out.check_output("Reason: Objective#SKIP", repetition=1)
    out.check_output("Reason: Solver#SKIP", repetition=1)
    out.check_output("Solver#RUN", repetition=1)


@pytest.mark.parametrize('component', ['objective', 'solver'])
@pytest.mark.parametrize('legacy', ['signature', 'tuple'])
def test_legacy_skip_warns(component, legacy):
    # Both deprecated forms warn: receiving the data, or returning a tuple.
    on_data = legacy == 'signature'
    obj_signature = "X, y" if on_data else "dataset"
    solver_signature = "**obj" if on_data else "objective, dataset"
    objective = f"""from benchopt.utils.temp_benchmark import TempObjective

        class Objective(TempObjective):
            def skip(self, {obj_signature}): return True, "LEGACY#SKIP"
    """
    solver = f"""from benchopt.utils.temp_benchmark import TempSolver

        class Solver(TempSolver):
            name = "test-solver"
            def skip(self, {solver_signature}): return True, "LEGACY#SKIP"
    """
    components = (
        dict(objective=objective) if component == 'objective'
        else dict(solvers=[solver])
    )
    match = f"{component.capitalize()}.skip"
    # Every run is skipped, so the run produces no result and exits with 1.
    with temp_benchmark(**components) as benchmark, \
            CaptureCmdOutput(exit=1) as out:
        with pytest.warns(FutureWarning, match=match):
            run([*(
                f'{benchmark.benchmark_dir} -s test-solver -d test-dataset '
                '--no-plot'
            ).split()], standalone_mode=False)

    out.check_output("Reason: LEGACY#SKIP", repetition=1)
