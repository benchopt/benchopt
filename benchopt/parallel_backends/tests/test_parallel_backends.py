import sys
import pytest


from benchopt.cli.main import run
from benchopt.utils.temp_benchmark import temp_benchmark

from benchopt.tests.utils import CaptureCmdOutput, patch_import


@pytest.mark.parametrize("backend", ["submitit", "dask"])
def test_backend_not_installed(backend):
    config = f"""
    backend: {backend}
    """

    def raise_error():
        raise ImportError("important debug message")

    # Remove imported modules to force re-import
    for k in list(sys.modules):
        modules = ['parallel_backends', 'submitit', 'distributed', 'dask']
        if any(m in k for m in modules):
            print("removing", k)
            del sys.modules[k]
    with patch_import(submitit=raise_error, distributed=raise_error):
        with temp_benchmark(config={"parallel_config.yml": config}) as bench:
            parallel_config_file = bench.benchmark_dir / "parallel_config.yml"
            msg = f"pip install benchopt.{backend}."
            with pytest.raises(ImportError, match=msg):
                run([
                    str(bench.benchmark_dir),
                    *"-s test-solver -d test-dataset -n 0 -r 1 --no-plot "
                    f"--parallel-config {parallel_config_file}".split()
                ], standalone_mode=False)


def test_missing_backend():
    parallel_config = """
    param1: 1
    """
    solver1 = """from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = "solver1"
        sampling_strategy = "iteration"
        def set_objective(self, X, y, lmbd): self.n_features = X.shape[1]
        def run(self, n_iter): pass
        def get_result(self):
            return {"beta": np.zeros(self.n_features)}
    """

    with temp_benchmark(
            solvers=[solver1],
            config={"parallel_config.yml": parallel_config}
    ) as benchmark:
        parallel_config_file = benchmark.benchmark_dir / "parallel_config.yml"
        with CaptureCmdOutput():
            msg = "Could not find `backend` specification "
            with pytest.raises(AssertionError, match=msg):
                run([
                    str(benchmark.benchmark_dir),
                    *"-s solver1 -d test-dataset -n 0 -r 1 --no-plot "
                    f"--parallel-config {parallel_config_file}".split()
                ], standalone_mode=False)


def test_dask_backend():
    distributed = pytest.importorskip("distributed")
    client_name = 'benchopt-tests'
    n_workers = 2
    parallel_config = f"""backend: dask
    dask_name: {client_name}
    dask_n_workers: {n_workers}
    """
    solver1 = """from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = "solver1"
        sampling_strategy = "iteration"
        def set_objective(self, X, y, lmbd): pass
        def run(self, n_iter): pass
        def get_result(self):
            from distributed import get_client
            client = get_client()
            assert "Client-worker" in client.id, client.id
            print(client.id)
            return {"beta": 1}
    """

    with temp_benchmark(
            solvers=[solver1],
            config={"parallel_config.yml": parallel_config}
    ) as benchmark:
        parallel_config_file = benchmark.benchmark_dir / "parallel_config.yml"
        with CaptureCmdOutput() as out:
            run([
                str(benchmark.benchmark_dir),
                *"-s solver1 -d test-dataset -n 0 -r 1 --no-plot "
                f"--parallel-config {parallel_config_file}".split()
            ], standalone_mode=False)

    client = distributed.get_client()
    effective_workers = len(client._scheduler_identity.get('workers', {}))
    assert client_name in client.id
    assert effective_workers == n_workers
    client.close()

    out.check_output("Distributed run with backend: dask", repetition=1)
    out.check_output(client_name, repetition=0)


def test_submitit_backend():
    pytest.importorskip("submitit")

    parallel_config = "backend: submitit"
    solver1 = """from benchopt import BaseSolver
    import submitit
    import numpy as np

    class Solver(BaseSolver):
        name = "solver1"
        sampling_strategy = "iteration"
        def set_objective(self, X, y, lmbd): pass
        def run(self, n_iter): pass
        def get_result(self):
            # This will fail if not run in a submitit worker
            job_env = submitit.JobEnvironment()
            return {"beta": 1}
    """

    with temp_benchmark(
            solvers=[solver1],
            config={"parallel_config.yml": parallel_config}
    ) as benchmark:
        parallel_config_file = benchmark.benchmark_dir / "parallel_config.yml"
        with CaptureCmdOutput() as out:
            run([
                str(benchmark.benchmark_dir),
                *"-s solver1 -d test-dataset -n 0 -r 1 --no-plot "
                f"--parallel-config {parallel_config_file}".split()
            ], standalone_mode=False)

    out.check_output("Distributed run with backend: submitit", repetition=1)
