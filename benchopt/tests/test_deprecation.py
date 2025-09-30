import pytest

from benchopt import __version__
from benchopt.cli.main import run
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.utils.conda_env_cmd import get_env_file_from_requirements

from benchopt.tests.utils import CaptureCmdOutput


##############################################################################
# Deprecation check for benchopt 1.8
# XXX: remove in benchopt 1.8


def test_deprecated_channel_spec():
    with pytest.warns(DeprecationWarning):
        env = get_env_file_from_requirements(["chan:pkg"])
    assert env == "channels:\n  - chan\ndependencies:\n  - pkg"

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
        "channels:\n  - chan\n"
        "dependencies:\n  - pkg1\n  - pkg2\n  - pip\n  - pip:\n    - pkg3"
    )


# TODO: remove this test in benchopt 1.8
def test_deprecated_safe_import_context(no_raise_install):
    solver = """from benchopt import BaseSolver
        from benchopt import safe_import_context

        with safe_import_context() as import_ctx:
            import fake_module

        class Solver(BaseSolver):
            name = 'test-solver'
            def set_objective(self, X, y, lmbd): pass
            def run(self, n_iter): pass
            def get_result(self): return {'beta': 1}
    """

    with temp_benchmark(solvers=solver) as bench:
        with pytest.warns(DeprecationWarning, match="safe_import_context"):
            with pytest.raises(SystemExit, match='1'):
                run(
                    f"{bench.benchmark_dir} -s test-solver -d test-dataset"
                    " -n 1 -r 1 --no-plot".split(), standalone_mode=False
                )


##############################################################################
# Deprecation check for benchopt 1.9
# XXX: remove in benchopt 1.9

def test_slurm_deprecation():
    pytest.importorskip("submitit")

    slurm_config = """
    timeout_min: 1
    """

    with temp_benchmark(config={'slurm.yml': slurm_config}) as bench:
        slurm_config_file = bench.benchmark_dir / "slurm.yml"
        with CaptureCmdOutput():
            msg = "Cannot use both `--slurm` and `--parallel-backend`."
            with pytest.raises(AssertionError, match=msg):
                run(
                    f"{bench.benchmark_dir} -d test-dataset -n 0 -r 5 "
                    f"--no-plot --slurm {slurm_config_file} "
                    f"--parallel-config {slurm_config_file}".split(),
                    standalone_mode=False)

        with CaptureCmdOutput():
            msg = "`--slurm` is deprecated, use `--parallel-backend` instead."
            with pytest.warns(DeprecationWarning, match=msg):
                run(
                    f"{bench.benchmark_dir} -d test-dataset -n 0 -r 5 "
                    f"--no-plot --slurm {slurm_config_file}".split(),
                    standalone_mode=False)
