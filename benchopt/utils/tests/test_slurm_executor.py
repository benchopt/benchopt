import pytest
import yaml
from benchopt.tests import DUMMY_BENCHMARK
from benchopt.utils.slurm_executor import (
    get_slurm_executor,
    run_on_slurm,
)
from submitit.slurm.test_slurm import mocked_slurm


@pytest.fixture
def dummy_slurm_config(tmp_path):
    config = {
        "slurm_time": "00:10",
        "slurm_partition": "test_partition",
        "slurm_nodes": 1,
    }
    config_path = tmp_path / "slurm.yaml"
    config_path.write_text(yaml.dump(config))
    return config_path


@pytest.fixture
def dummy_solver():
    class DummySolver:
        slurm_params = {
            "slurm_time": "00:01",
            "slurm_nodes": 2,
            "slurm_mem": "1234MB",
        }

    return DummySolver()


def test_get_slurm_executor(dummy_slurm_config, dummy_solver):
    # Test witthout solver overrides
    with mocked_slurm():
        executor = get_slurm_executor(
            DUMMY_BENCHMARK, dummy_slurm_config, solver=None
        )
    assert executor._executor.parameters["time"] == "00:10"
    assert executor._executor.parameters["partition"] == "test_partition"
    assert executor._executor.parameters["nodes"] == 1

    # Test with solver overrides
    with mocked_slurm():
        executor_override = get_slurm_executor(
            DUMMY_BENCHMARK, dummy_slurm_config, solver=dummy_solver
        )
    assert executor_override._executor.parameters["time"] == "00:01"
    assert (
        executor_override._executor.parameters["partition"] == "test_partition"
    )
    assert executor_override._executor.parameters["nodes"] == 2
    assert executor_override._executor.parameters["mem"] == "1234MB"


def test_run_on_slurm(dummy_slurm_config, dummy_solver):
    def dummy_solver_runner(*args, **kwargs):
        return "done"

    # Run the function
    res = run_on_slurm(
        benchmark=DUMMY_BENCHMARK,
        slurm_config=dummy_slurm_config,
        run_one_solver=dummy_solver_runner,
        common_kwargs={"timeout": None},
        all_runs=[{"solver": dummy_solver}],
    )

    assert len(res) == 1
    assert res[0] == "done"
