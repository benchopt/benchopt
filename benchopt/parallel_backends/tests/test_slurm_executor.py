import pytest

from benchopt.runner import run_benchmark
from benchopt.tests.utils import CaptureCmdOutput
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.results import read_results

submitit = pytest.importorskip("submitit")

from submitit.slurm.test_slurm import mocked_slurm  # noqa: E402
from benchopt.parallel_backends.slurm_executor import (  # noqa: E402
    _group_runs,
    _run_batch,
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
    # `run_one_solver` returns a (results, key, status, msg) tuple where
    # `results` is a list of run-statistics dicts. Only annotate those dicts
    # with the SLURM config used to run the job.
    if isinstance(result, tuple):
        res, *rest = result
        res = _annotate_task_result(res, config)
        return (res, *rest)
    if isinstance(result, list):
        return [_annotate_task_result(item, config) for item in result]
    if isinstance(result, dict):
        return {**result, **{f"s_{k}": v for k, v in config.items()}}
    return result


class MockedTask:
    """Stand-in for a submitit job future, used by the slurm tests."""

    job_id = "fake"

    def __init__(self, func, args, kwargs, config):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.config = config

    def done(self): return True
    def exception(self): return None
    def cancel(self): return None

    def results(self):
        result = self.func(*self.args, **self.kwargs)
        return [_annotate_task_result(result, self.config)]


@pytest.fixture
def mocked_submitit(monkeypatch):
    """Capture submitit submissions and run them locally, returning the list
    of captured submissions for inspection.
    """
    submissions = []

    def submit(self, func, *args, **kwargs):
        config = self._executor.parameters
        submissions.append(
            dict(func=func, args=args, kwargs=kwargs, config=config)
        )
        return MockedTask(func, args, kwargs, config)

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


def test_run_on_slurm(mocked_submitit, dummy_slurm_config):
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


@pytest.mark.parametrize("batch_n_jobs", [1, 2])
def test_run_on_slurm_grouped(mocked_submitit, batch_n_jobs):
    # Two solvers sharing the same SLURM config should be grouped into a
    # single submitted job, and `batch_n_jobs` should propagate to _run_batch.
    parallel_config = {
        "backend": "submitit",
        "group_by": "dataset",
        "batch_n_jobs": batch_n_jobs,
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
                dataset_names=["test-dataset"], max_runs=0, timeout=None,
                parallel_config=parallel_config, plot_result=False,
            )
        df = read_results(out.result_files[0])

    # Both solvers ran (df has one row per solver) but they were collapsed
    # into a single SLURM submission.
    assert len(df) == 2
    assert len(mocked_submitit) == 1
    sub = mocked_submitit[0]
    assert sub["func"] is _run_batch
    assert sub["kwargs"]["n_jobs"] == batch_n_jobs


def test_run_on_slurm_grouped_keeps_separate_slurm_configs(mocked_submitit):
    # Solvers in the same `group_by` bucket but with different SLURM configs
    # must end up in separate SLURM jobs, so each solver keeps its own config.
    parallel_config = {
        "backend": "submitit",
        "group_by": "dataset",
        "slurm_nodes": 1,
    }
    solver = """
        from benchopt.utils.temp_benchmark import TempSolver

        class Solver(TempSolver):
            name = "{name}"
            {slurm_params}
    """
    solvers = [
        solver.format(name='solver_default', slurm_params=""),
        solver.format(
            name='solver_custom',
            slurm_params="slurm_params = {'slurm_nodes': 2}",
        ),
    ]

    with temp_benchmark(solvers=solvers) as bench, mocked_slurm():
        with CaptureCmdOutput(delete_result_files=False) as out:
            run_benchmark(
                bench.benchmark_dir, ["solver_default", "solver_custom"],
                dataset_names=["test-dataset"], max_runs=0, timeout=None,
                parallel_config=parallel_config, plot_result=False,
            )
        df = read_results(out.result_files[0]).set_index("solver_name")

    # Each solver kept its own slurm_nodes value; if they had been grouped
    # into one job, they would share the same SLURM config.
    assert df.loc["solver_default", "s_nodes"] == 1
    assert df.loc["solver_custom", "s_nodes"] == 2


def test_group_runs_without_meta_does_not_crash():
    # The dataset-preparation path submits kwargs without run metadata; a
    # `group_by` config must not crash there (KeyError: 'meta') -- grouping is
    # meaningless without a run, so each kwargs gets its own job.
    prepare_kwargs = [
        {"benchmark": None, "dataset": "d1", "force": False},
        {"benchmark": None, "dataset": "d2", "force": False},
    ]
    groups = _group_runs(prepare_kwargs, {}, group_by="dataset")
    assert len(groups) == 2
    assert all(len(runs) == 1 for _cfg, runs in groups)


@pytest.mark.parametrize("batch_n_jobs, expected_waves", [(1, 2), (2, 1)])
def test_run_on_slurm_grouped_scales_walltime(
    mocked_submitit, batch_n_jobs, expected_waves
):
    # A batched job runs its group in ceil(len(group) / batch_n_jobs) waves,
    # so its SLURM wall-time (slurm_time) must be sized for the whole batch,
    # not a single run. Two solvers grouped by dataset into one job:
    # serially (batch_n_jobs=1) that is 2 * timeout, in parallel it is 1.
    timeout = 100
    parallel_config = {
        "backend": "submitit",
        "group_by": "dataset",
        "batch_n_jobs": batch_n_jobs,
    }
    solver = """
        from benchopt.utils.temp_benchmark import TempSolver

        class Solver(TempSolver):
            name = "{name}"
    """
    solvers = [solver.format(name="solver_1"), solver.format(name="solver_2")]

    with temp_benchmark(solvers=solvers) as bench, mocked_slurm():
        with CaptureCmdOutput(delete_result_files=False):
            run_benchmark(
                bench.benchmark_dir, ["solver_1", "solver_2"],
                dataset_names=["test-dataset"], max_runs=0, timeout=timeout,
                parallel_config=parallel_config, plot_result=False,
            )

    # Both solvers collapsed into a single job whose wall-time is scaled by the
    # number of serial waves, matching get_slurm_executor's `1.5 * timeout`.
    assert len(mocked_submitit) == 1
    slurm_time = mocked_submitit[0]["config"]["time"]
    assert slurm_time == f"00:{int(1.5 * expected_waves * timeout)}"
