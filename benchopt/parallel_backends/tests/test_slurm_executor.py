import pytest

from benchopt.runner import run_benchmark
from benchopt.tests.utils import CaptureCmdOutput
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.results import read_results

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


def _annotate_task_result(result, config):
    if isinstance(result, list):
        return [_annotate_task_result(item, config) for item in result]
    if isinstance(result, dict):
        return {**result, **{f"s_{k}": v for k, v in config.items()}}
    return result


def _patch_submitit_submit(monkeypatch):
    submissions = []

    class MockedTask:

        def __init__(self, task, config):
            self.job_id = "fake"
            self.task = task
            self.config = config

        def done(self): return True
        def exception(self): return None
        def cancel(self): return None

        def results(self):
            func, args, kwargs = self.task
            return [_annotate_task_result(func(*args, **kwargs), self.config)]

    def submit(self, func, *args, **kwargs):
        submissions.append(
            dict(
                func=func,
                args=args,
                kwargs=kwargs,
                config=self._executor.parameters,
            )
        )
        return MockedTask((func, args, kwargs), self._executor.parameters)

    monkeypatch.setattr("submitit.AutoExecutor.submit", submit)
    monkeypatch.setattr(
        "submitit.helpers.as_completed.__defaults__", (None, 0.1)
    )
    return submissions


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
    from benchopt.utils.temp_benchmark import TempSolver

    class Solver(TempSolver):
        name = "dummy"
        slurm_params = {
            "slurm_time": "00:01",
            "slurm_nodes": 2,
            "slurm_mem": "1234MB",
        }
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
    _patch_submitit_submit(monkeypatch)

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
        from benchopt.utils.temp_benchmark import TempSolver

        class Solver(TempSolver):
            name = "{name}"
            {parameters}
            {slurm_params}
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
        df = read_results(out.result_files[0]).set_index("solver_name")

    assert len(df) == 6

    # Default parameter from global config is never overidden
    assert (df['s_gres'] == "gpu:1").all()

    # If no parameters and no slurm_params, no override of global config
    p_default = df.loc['solver_no_params'].fillna("")
    for p in ["nodes", "time", "mem"]:
        assert p_default[f"s_{p}"] == parallel_config.get(f"slurm_{p}", "")

    # If slurm_params is set, it is used as a global config
    p_slurm_params = df.loc["solver_slurm_params"].fillna("")
    for p in ["nodes", "time", "mem"]:
        assert p_slurm_params[f"s_{p}"] == slurm_params.get(f"slurm_{p}", "")

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


def test_run_on_slurm_grouped_batches_runs(monkeypatch):
    submissions = _patch_submitit_submit(monkeypatch)

    parallel_config = {
        "backend": "submitit",
        "group_by": "dataset",
        "batch_n_jobs": 1,
    }

    solver = """
        from benchopt.utils.temp_benchmark import TempSolver

        class Solver(TempSolver):
            name = "{name}"
    """
    solvers = [solver.format(name="solver_1"), solver.format(name="solver_2")]

    with temp_benchmark(solvers=solvers) as bench, mocked_slurm():
        with CaptureCmdOutput(delete_result_files=False) as out:
            run_benchmark(
                bench.benchmark_dir, ["solver_1", "solver_2"],
                dataset_names=["test-dataset"],
                max_runs=0,
                timeout=None,
                parallel_config=parallel_config,
                plot_result=False,
            )
        df = read_results(out.result_files[0])

    assert len(df) == 2
    assert len(submissions) == 1
    assert submissions[0]["func"].__name__ == "_run_batch"
    assert len(submissions[0]["args"][2]) == 2
    assert submissions[0]["args"][3] == 1


def test_run_on_slurm_grouped_keeps_separate_slurm_configs(monkeypatch):
    submissions = _patch_submitit_submit(monkeypatch)

    parallel_config = {
        "backend": "submitit",
        "group_by": "dataset",
        "batch_n_jobs": 1,
        "slurm_nodes": 1,
    }

    solver = """
        from benchopt.utils.temp_benchmark import TempSolver

        class Solver(TempSolver):
            name = "{name}"
            {slurm_params}
    """
    solvers = [
        solver.format(name="solver_default", slurm_params=""),
        solver.format(
            name="solver_custom",
            slurm_params="slurm_params = {'slurm_nodes': 2}",
        ),
    ]

    with temp_benchmark(solvers=solvers) as bench, mocked_slurm():
        run_benchmark(
            bench.benchmark_dir, ["solver_default", "solver_custom"],
            dataset_names=["test-dataset"],
            max_runs=0,
            timeout=None,
            parallel_config=parallel_config,
            plot_result=False,
        )

    assert len(submissions) == 2
    assert all(sub["func"].__name__ == "_run_batch" for sub in submissions)
    assert sorted(len(sub["args"][2]) for sub in submissions) == [1, 1]
    assert sorted(sub["config"]["nodes"] for sub in submissions) == [1, 2]


def test_run_on_slurm_grouped_batch_parallelism(monkeypatch):
    submissions = _patch_submitit_submit(monkeypatch)

    parallel_config = {
        "backend": "submitit",
        "group_by": "dataset",
        "batch_n_jobs": 2,
    }

    solver = """
        from benchopt.utils.temp_benchmark import TempSolver

        class Solver(TempSolver):
            name = "solver"
            parameters = {"p": [0, 1]}
    """

    with temp_benchmark(solvers=solver) as bench, mocked_slurm():
        with CaptureCmdOutput(delete_result_files=False) as out:
            run_benchmark(
                bench.benchmark_dir, ["solver[p=0]", "solver[p=1]"],
                dataset_names=["test-dataset"],
                max_runs=0,
                timeout=None,
                parallel_config=parallel_config,
                plot_result=False,
            )
        df = read_results(out.result_files[0])

    assert len(df) == 2
    assert len(submissions) == 1
    assert submissions[0]["func"].__name__ == "_run_batch"
    assert len(submissions[0]["args"][2]) == 2
    assert submissions[0]["args"][3] == 2
