import pytest

from benchopt import BaseSolver
from benchopt.helpers.requires_gpu import gpu_available
from benchopt.utils.run_context import RunContext


class Solver(BaseSolver):
    name = "gpu-solver"
    parameters = {"slurm_gpus_per_task": [0]}

    def set_objective(self):
        pass

    def run(self, _):
        pass

    def get_result(self):
        return {}


def check_gpu(component, parallel_config):
    """Call `gpu_available` in a run of ``component`` with this config."""
    with RunContext(parallel_config=parallel_config).set_run_context(
        objective=None, dataset=None, solver=component, repetition=0,
        base_seed=0,
    ):
        return gpu_available(component)


@pytest.mark.parametrize("has_cuda", [True, False])
def test_gpu_available_local(monkeypatch, has_cuda):
    monkeypatch.setattr(
        "benchopt.helpers.requires_gpu.get_cuda_version",
        lambda: "cuda_12.4" if has_cuda else None,
    )
    config = {"backend": "loky", "n_jobs": 2}
    assert check_gpu(Solver.get_instance(), config) is has_cuda


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
    monkeypatch, config, slurm_params, parameters, expected
):
    pytest.importorskip("submitit")
    # The front node has no GPU, only the requested workers.
    monkeypatch.setattr(
        "benchopt.helpers.requires_gpu.get_cuda_version", lambda: None
    )
    monkeypatch.setattr(Solver, "slurm_params", slurm_params, raising=False)
    config = {"backend": "submitit", "group_by": ["dataset"], **config}
    assert check_gpu(Solver.get_instance(**parameters), config) is expected


def test_gpu_available_dask(monkeypatch):
    monkeypatch.setattr(
        "benchopt.helpers.requires_gpu.get_cuda_version", lambda: None
    )
    assert check_gpu(Solver.get_instance(), {"backend": "dask"})


def test_gpu_available_unknown_backend():
    with pytest.raises(ValueError, match="Unknown parallel backend 'ray'"):
        check_gpu(Solver.get_instance(), {"backend": "ray"})


def test_gpu_available_outside_run():
    # The worker config depends on the run, so it needs its context.
    with pytest.raises(RuntimeError, match="get_run_component"):
        gpu_available(Solver.get_instance())
