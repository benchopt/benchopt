import pytest

from benchopt import __version__
from benchopt.cli.main import run
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.utils.conda_env_cmd import get_env_file_from_requirements

from benchopt.tests.utils import CaptureRunOutput


##############################################################################
# Deprecation check for benchopt 1.8
# XXX: remove in benchopt 1.8

def test_slurm_deprecation():
    assert __version__ < "1.8"
    pytest.importorskip("submitit")

    slurm_config = """
    timeout_min: 1
    """
    solver1 = """from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = 'solver1'
        sampling_strategy = 'iteration'
        def set_objective(self, X, y, lmbd): self.n_features = X.shape[1]
        def run(self, n_iter): pass
        def get_result(self):
            return {'beta': np.zeros(self.n_features)}
    """

    with temp_benchmark(
            solvers=[solver1],
            config={'slurm.yml': slurm_config}
    ) as benchmark:
        slurm_config_file = benchmark.benchmark_dir / "slurm.yml"
        with CaptureRunOutput():
            msg = "Cannot use both `--slurm` and `--parallel-backend`."
            with pytest.raises(AssertionError, match=msg):
                run([
                    str(benchmark.benchmark_dir),
                    *'-s solver1 -d test-dataset -n 0 -r 5 --no-plot '
                    f'-o dummy*[reg=0.5] --slurm {slurm_config_file} '
                    f'--parallel-config {slurm_config_file}'.split()
                ], standalone_mode=False)

        with CaptureRunOutput():
            msg = "`--slurm` is deprecated, use `--parallel-backend` instead."
            with pytest.warns(DeprecationWarning, match=msg):
                run([
                    str(benchmark.benchmark_dir),
                    *'-s solver1 -d test-dataset -n 0 -r 5 --no-plot '
                    f'-o dummy*[reg=0.5] --slurm {slurm_config_file}'.split()
                ], standalone_mode=False)


def test_deprecated_channel_spec():
    assert __version__ < "1.8"
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

    with temp_benchmark(solvers=solver) as benchmark:
        with pytest.warns(DeprecationWarning, match="safe_import_context"):
            with pytest.raises(SystemExit, match='1'):
                run(
                    f"{benchmark.benchmark_dir} -s test-solver -d test-dataset"
                    " -n 1 -r 1 --no-plot".split(), standalone_mode=False
                )
