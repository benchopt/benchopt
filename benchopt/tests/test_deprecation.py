import pytest


from benchopt import __version__
from benchopt.cli.main import run
from benchopt.utils.temp_benchmark import temp_benchmark

from benchopt.tests.utils import CaptureRunOutput


##############################################################################
# Deprecation check for benchopt 1.7
# XXX: remove in benchopt 1.7

def test_slurm_deprecation():
    assert __version__ < "1.7"
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
