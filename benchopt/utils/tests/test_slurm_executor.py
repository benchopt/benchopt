import pytest
from benchopt.utils.slurm_executor import (
    get_slurm_executor,
    run_on_slurm,
    merge_configs,
)
from benchopt.utils.temp_benchmark import temp_benchmark

submitit = pytest.importorskip("submitit")
from submitit.slurm.test_slurm import mocked_slurm  # noqa: E402


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

    with temp_benchmark() as bench:
        # Test without solver overrides
        with mocked_slurm():
            executor = get_slurm_executor(bench, dummy_slurm_config)
    parameters = executor._executor.parameters
    assert parameters["time"] == dummy_slurm_config["slurm_time"]
    assert parameters["partition"] == dummy_slurm_config["slurm_partition"]
    assert parameters["nodes"] == dummy_slurm_config["slurm_nodes"]


def test_merge_configs(dummy_solver, dummy_slurm_config):
    # Test with solver overrides
    config_override = merge_configs(dummy_slurm_config, dummy_solver)

    with temp_benchmark() as bench:
        with mocked_slurm():
            executor = get_slurm_executor(bench, config_override)

    parameters = executor._executor.parameters
    assert parameters["time"] == dummy_solver.slurm_params["slurm_time"]
    assert parameters["nodes"] == dummy_solver.slurm_params["slurm_nodes"]
    assert parameters["mem"] == dummy_solver.slurm_params["slurm_mem"]
    assert parameters["partition"] == dummy_slurm_config["slurm_partition"]


def test_run_on_slurm(monkeypatch, dummy_solver, dummy_slurm_config):

    class MockedTask:
        def __init__(self, config):
            self.job_id = "12"
            self.config = config

        def done(self): return True
        def exception(self): return None
        def result(self): return self.config

    def submit(self, *args, **kwargs):
        # Mock submit to return a mocked task, with the executor's parameters
        return MockedTask(self._executor.parameters)
    monkeypatch.setattr(submitit.AutoExecutor, 'submit', submit)

    # Run the function
    config = {'slurm_config': dummy_slurm_config}
    with temp_benchmark(config=config) as bench:
        with mocked_slurm():
            res = run_on_slurm(
                benchmark=bench,
                slurm_config=bench.benchmark_dir / "slurm_config.yml",
                run_one_solver=lambda **kwargs: "done",
                common_kwargs={"timeout": None},
                all_runs=[
                    {"solver": dummy_solver},
                    {"solver": None}
                ],
            )

    assert len(res) == 2
    p_overwrite = res[0]

    assert p_overwrite["time"] == dummy_solver.slurm_params["slurm_time"]
    assert p_overwrite["nodes"] == dummy_solver.slurm_params["slurm_nodes"]
    assert p_overwrite["mem"] == dummy_solver.slurm_params["slurm_mem"]
    assert p_overwrite["partition"] == dummy_slurm_config["slurm_partition"]

    p_default = res[1]
    assert p_default["time"] == dummy_slurm_config["slurm_time"]
    assert p_default["nodes"] == dummy_slurm_config["slurm_nodes"]
    assert p_default["partition"] == dummy_slurm_config["slurm_partition"]
