import pytest

from benchopt.runner import run_benchmark
from benchopt.tests.utils import CaptureCmdOutput
from benchopt.utils.temp_benchmark import temp_benchmark

submitit = pytest.importorskip("submitit")

from submitit.slurm.test_slurm import mocked_slurm  # noqa: E402
from benchopt.parallel_backends.slurm_executor import (  # noqa: E402
    get_slurm_executor,
    get_solver_slurm_config,
)


@pytest.fixture
def dummy_slurm_config():
    return {
        "slurm_time": "00:10",
        "slurm_partition": "test_partition",
        "slurm_nodes": 1,
        "slurm_additional_parameters": {
            "slurm_mem": "1000MB",
            "slurm_gres": "gpu:1",
        },
    }


@pytest.fixture
def dummy_solver():
    class DummySolver:
        slurm_params = {
            "slurm_time": "00:01",
            "slurm_nodes": 2,
            "slurm_mem": "1234MB",
        }

    return DummySolver()


def test_get_slurm_executor(dummy_slurm_config):

    with mocked_slurm(), temp_benchmark() as bench:
        executor = get_slurm_executor(bench, dummy_slurm_config)
    parameters = executor._executor.parameters
    assert parameters["time"] == dummy_slurm_config["slurm_time"]
    assert parameters["partition"] == dummy_slurm_config["slurm_partition"]
    assert parameters["nodes"] == dummy_slurm_config["slurm_nodes"]


def test_merge_configs(dummy_slurm_config):
    # Test with solver overrides
    solver = """
    from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = "dummy"
        slurm_params = {
            "slurm_time": "00:01",
            "slurm_nodes": 2,
            "slurm_mem": "1234MB",
        }
        def set_objective(self, **kwargs): pass
        def run(self, _): pass
        def get_result(self): return dict(beta=1)
    """

    with mocked_slurm(), temp_benchmark(solvers=solver) as bench:
        solver = bench.get_solvers()[0].get_instance()
        config_override = get_solver_slurm_config(solver, dummy_slurm_config)
        executor = get_slurm_executor(bench, config_override)

    parameters = executor._executor.parameters
    assert parameters["time"] == solver.slurm_params["slurm_time"]
    assert parameters["nodes"] == solver.slurm_params["slurm_nodes"]
    assert parameters["mem"] == solver.slurm_params["slurm_mem"]
    assert parameters["partition"] == dummy_slurm_config["slurm_partition"]


def test_run_on_slurm(monkeypatch, dummy_slurm_config):

    class MockedTask:

        def __init__(self, task, config):
            self.job_id = "fake"
            self.task = task
            self.config = config

        def done(self): return True
        def exception(self): return None

        # Result return as many information about the run as possible
        # Need to output a list for `results`, and benchopt also expect
        # a list from `run_one_solver`
        def results(self):
            func, args, kwargs = self.task
            res = func(*args, **kwargs)
            res = [
                {**r, **{f"s_{k}": v for k, v in self.config.items()}}
                for r in res
            ]

            return [res]

    # Fake submit to allow running as on a slurm cluster and
    # get the configuration back
    def submit(self, func, *args, **kwargs):
        # Mock submit to return a mocked task, with the executor's parameters
        return MockedTask((func, args, kwargs), self._executor.parameters)

    monkeypatch.setattr("submitit.AutoExecutor.submit", submit)
    monkeypatch.setattr(
        "submitit.helpers.as_completed.__defaults__", (None, 0.1)
    )

    parallel_config = {
        "backend": "submitit",
        "slurm_nodes": 1,
        "slurm_gres": "gpu:1",
    }

    slurm_params = {
        "slurm_time": "00:01",
        "slurm_nodes": 2,
        "slurm_mem": "1234MB",
    }
    my_params = {"p": [0, 1], "slurm_nodes": [3]}
    slurm_params_str = f"slurm_params = {slurm_params}"
    my_params_str = f"parameters = {my_params}"

    solver = """
        from benchopt import BaseSolver

        class Solver(BaseSolver):
            name = "{name}"
            {parameters}
            {slurm_params}
            def set_objective(self, **kwargs): pass
            def run(self, _): pass
            def get_result(self): return dict(beta=1)
    """
    solvers = [
        solver.format(name='solver_no_params', parameters="", slurm_params=""),
        solver.format(
            name='solver_slurm_params', parameters="",
            slurm_params=slurm_params_str
        ),
        solver.format(
            name='solver_my_params', parameters=my_params_str, slurm_params=""
        ),
        solver.format(
            name='solver_all_params', parameters=my_params_str,
            slurm_params=slurm_params_str
        ),
    ]

    # Run the function on a mocked slurm cluster
    with temp_benchmark(solvers=solvers) as bench, mocked_slurm():
        with CaptureCmdOutput(delete_result_files=False) as out:
            run_benchmark(
                bench.benchmark_dir, [
                    "solver_no_params", "solver_slurm_params",
                    "solver_my_params[p=2]",
                    "solver_my_params[p=2,slurm_nodes=4]",
                    "solver_all_params[p=2]",
                    "solver_all_params[p=2,slurm_nodes=4]"
                ], dataset_names=["test-dataset"],
                max_runs=0,
                timeout=None,
                parallel_config=parallel_config,
                plot_result=False,
            )

        # Get the results
        import pandas as pd
        df = pd.read_parquet(out.result_files[0]).set_index("solver_name")

    assert len(df) == 6

    # Default parameter from global config is never overidden
    assert (df['s_gres'] == "gpu:1").all()

    # If no parameters and no slurm_params, no override of global config
    p_default = df.loc['solver_no_params']
    for p in ["nodes", "time", "mem"]:
        assert p_default[f"s_{p}"] == parallel_config.get(f"slurm_{p}", None)

    # If slurm_params is set, it is used as a global config
    p_slurm_params = df.loc["solver_slurm_params"]
    for p in ["nodes", "time", "mem"]:
        assert p_slurm_params[f"s_{p}"] == slurm_params.get(f"slurm_{p}", None)

    # Check that parameters override works
    all_params = df.query("p_solver_p == 2")
    assert len(all_params) == 4
    assert all(all_params["p_solver_slurm_nodes"] == all_params["s_nodes"])

    # Check that default are either parallel_config or slurm_params
    p_my_params = df[df.index.str.contains("solver_my_params")]
    for p in ["time", "mem"]:
        assert all(
            p_my_params[f"s_{p}"].fillna("") ==
            parallel_config.get(f"slurm_{p}", "")
        )
    p_all_params = df[df.index.str.contains("solver_all_params")]
    for p in ["time", "mem"]:
        assert all(
            p_all_params[f"s_{p}"].fillna("") ==
            slurm_params.get(f"slurm_{p}", "")
        )
