import threading

import pytest


from benchopt.cli.main import run
from benchopt.parallel_backends import check_parallel_config
from benchopt.utils.temp_benchmark import temp_benchmark

from benchopt.tests.utils import CaptureCmdOutput, patch_import


def raise_error():
    raise ImportError("important debug message")


def test_missing_backend():
    parallel_config = """
    param1: 1
    """

    with temp_benchmark(
            config={"parallel_config.yml": parallel_config}
    ) as benchmark:
        parallel_config_file = benchmark.benchmark_dir / "parallel_config.yml"
        with CaptureCmdOutput():
            msg = "Could not find `backend` specification "
            with pytest.raises(AssertionError, match=msg):
                run(
                    f"{benchmark.benchmark_dir} -d test-dataset --no-plot "
                    f"--parallel-config {parallel_config_file} -n 0".split(),
                    standalone_mode=False
                )


@pytest.mark.parametrize(
    "yaml_slurm_time, expected_slurm_time",
    [
        ("10:00:00", "10:00:00"),
        ("10:30", "00:10:30"),
        ("00:10:30", "00:10:30"),
        ("1-00:30:01", "1-00:30:01"),
    ],
)
def test_check_parallel_config_yaml_slurm_time_parsing(
    tmp_path, yaml_slurm_time, expected_slurm_time
):
    parallel_config_file = tmp_path / "parallel_config.yml"
    parallel_config_file.write_text(
        "backend: submitit\n"
        f"slurm_time: {yaml_slurm_time}\n"
    )

    cfg = check_parallel_config(parallel_config_file, n_jobs=None)

    assert cfg["slurm_time"] == expected_slurm_time


@pytest.mark.parametrize("backend", ["submitit", "dask"])
def test_backend_not_installed(backend):
    config = f"""
    backend: {backend}
    """

    # Remove imported modules to force re-import
    with patch_import(
            submitit=raise_error, distributed=raise_error,
            rm_modules=['parallel_backends', 'submitit', 'distributed', 'dask']
    ):
        with temp_benchmark(config={"parallel_config.yml": config}) as bench:
            parallel_config_file = bench.benchmark_dir / "parallel_config.yml"
            msg = f"pip install benchopt.{backend}."
            with pytest.raises(ImportError, match=msg):
                run([
                    str(bench.benchmark_dir),
                    *"-d test-dataset -n 0 -r 1 --no-plot "
                    f"--parallel-config {parallel_config_file}".split()
                ], standalone_mode=False)


def test_parallel_run_dispatches_lazily():
    # parallel_run must not consume the whole kwargs generator before yielding
    # the first dispatched result; otherwise every run (with its loaded data)
    # would be held in memory at once on a single node.
    from benchopt.parallel_backends import parallel_run

    n_runs = 100
    # The generator hard-blocks its tail until `release` is set. If dispatch is
    # lazy, the first result still comes out from the unblocked prefix; if it
    # eagerly drained the generator, this would instead block. This makes the
    # laziness check deterministic even on a slow (e.g. macOS) CI runner.
    block_after = 20
    release = threading.Event()
    pulled = []

    def kwargs_gen():
        for i in range(n_runs):
            if i == block_after:
                release.wait(timeout=30)
            pulled.append(i)
            yield dict(i=i)

    def _run(i):
        return ([], (str(i), "obj", "solver"), "done", "")

    # Nothing is cached, so every run is dispatched.
    _run.check_call_in_cache = lambda **kwargs: False

    results = parallel_run(
        benchmark=None, run=_run, run_kwargs_generator=kwargs_gen(),
        config=dict(backend="loky", n_jobs=2),
    )
    try:
        next(results)
        # A result came out while the generator tail is still blocked, so at
        # most the unblocked prefix was pulled.
        assert len(pulled) <= block_after
    finally:
        release.set()
    # Drain the rest so the workers shut down cleanly.
    assert len(list(results)) == n_runs - 1


@pytest.mark.parametrize("backend", ["submitit", "dask"])
def test_backend_collect(backend):
    config = f"""
    backend: {backend}
    """

    # Remove imported modules to force re-import, should raise error if collect
    # tries to run on the specified backend
    with patch_import(
            submitit=raise_error, distributed=raise_error,
            rm_modules=['parallel_backends', 'submitit', 'distributed', 'dask']
    ):
        with temp_benchmark(config={"parallel_config.yml": config}) as bench:
            cmd = f"{bench.benchmark_dir} -d test-dataset -n 0 -r 1 --no-plot"
            parallel_config_file = bench.benchmark_dir / "parallel_config.yml"
            with CaptureCmdOutput() as out:
                run(cmd.split(), standalone_mode=False)
            out.check_output("test-solver:", repetition=4)
            with CaptureCmdOutput() as out:
                run(
                    f"{cmd} --collect --parallel-config {parallel_config_file}"
                    .split(), standalone_mode=False
                )
            out.check_output("test-solver:", repetition=1)


def test_dask_backend():
    distributed = pytest.importorskip("distributed")
    client_name = 'benchopt-tests'
    n_workers = 2
    parallel_config = f"""backend: dask
    dask_name: {client_name}
    dask_n_workers: {n_workers}
    """
    solver1 = """from benchopt.utils.temp_benchmark import TempSolver
    import numpy as np

    class Solver(TempSolver):
        name = "solver1"
        def run(self, _):
            from distributed import get_client
            client = get_client()
            assert "Client-worker" in client.id, client.id
            print(client.id)
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
    workers = client._scheduler_identity.get('workers', {})
    effective_workers = len(workers)
    assert client_name in client.id
    assert effective_workers == n_workers
    client.close()

    out.check_output("Distributed run with backend: dask", repetition=1)
    # The name of the client on the workers should be Client-worker-*, and not
    # the name set in the config (client_name)
    out.check_output(client_name, repetition=0)
    out.check_output("Client-worker-", repetition=1)


def test_submitit_backend(monkeypatch):
    pytest.importorskip("submitit")
    # Make as_completed fast, as default is to wait 10 secs between checks
    monkeypatch.setattr(
        "submitit.helpers.as_completed.__defaults__", (None, 0.1)
    )

    parallel_config = "backend: submitit"
    solver1 = """from benchopt.utils.temp_benchmark import TempSolver
    import submitit
    import numpy as np

    class Solver(TempSolver):
        name = "solver1"
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
