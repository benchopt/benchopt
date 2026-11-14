import pytest

from benchopt import BaseSolver
from benchopt.helpers.requires_gpu import gpu_available
from benchopt.parallel_backends import check_parallel_config


class Solver(BaseSolver):
    name = "gpu-solver"
    parameters = {"slurm_gpus_per_task": [0]}

    def set_objective(self):
        pass

    def run(self, _):
        pass

    def get_result(self):
        return {}


@pytest.fixture
def frontal():
    """Set the front node config of a run, and reset it after the test."""
    yield lambda config: check_parallel_config(config, None)
    check_parallel_config(None, None)


@pytest.mark.parametrize("has_cuda", [True, False])
def test_gpu_available_local(frontal, monkeypatch, has_cuda):
    monkeypatch.setattr(
        "benchopt.helpers.requires_gpu.get_cuda_version",
        lambda: "cuda_12.4" if has_cuda else None,
    )
    frontal({"backend": "loky", "n_jobs": 2})
    assert gpu_available(Solver.get_instance()) is has_cuda


@pytest.mark.parametrize("config, slurm_params, parameters, expected", [
    ({}, {}, {}, False),
    ({"slurm_gres": "gpu:1"}, {}, {}, True),
    ({"slurm_gres": "shard:1"}, {}, {}, False),
    ({"slurm_cpus_per_gpu": 4}, {}, {}, False),
    ({"gpus_per_node": 1}, {}, {}, True),
    ({"slurm_additional_parameters": {"gpus-per-node": 1}}, {}, {}, True),
    ({}, {"slurm_gres": "gpu:1"}, {}, True),
    ({}, {}, {"slurm_gpus_per_task": 1}, True),
    ({"slurm_gres": "gpu:1"}, {"slurm_gres": ""}, {}, False),
])
def test_gpu_available_submitit(
    frontal, monkeypatch, config, slurm_params, parameters, expected
):
    pytest.importorskip("submitit")
    # The front node has no GPU, only the requested workers.
    monkeypatch.setattr(
        "benchopt.helpers.requires_gpu.get_cuda_version", lambda: None
    )
    monkeypatch.setattr(Solver, "slurm_params", slurm_params, raising=False)
    frontal({"backend": "submitit", "group_by": ["dataset"], **config})
    assert gpu_available(Solver.get_instance(**parameters)) is expected


def test_gpu_available_dask(frontal, monkeypatch):
    monkeypatch.setattr(
        "benchopt.helpers.requires_gpu.get_cuda_version", lambda: None
    )
    frontal({"backend": "dask"})
    assert gpu_available(Solver.get_instance())
