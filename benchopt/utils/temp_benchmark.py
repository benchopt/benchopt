import os
import tempfile
import contextlib

from pathlib import Path

from benchopt.benchmark import Benchmark
from benchopt.tests import DUMMY_BENCHMARK_PATH


dummy_objective = (DUMMY_BENCHMARK_PATH / 'objective.py').read_text()

dummy_solvers = [
    (DUMMY_BENCHMARK_PATH / "solvers" / p).read_text()
    for p in os.listdir(DUMMY_BENCHMARK_PATH / "solvers")
    if p.endswith(".py")
]

dummy_datasets = [
    (DUMMY_BENCHMARK_PATH / "datasets" / p).read_text()
    for p in os.listdir(DUMMY_BENCHMARK_PATH / "datasets")
    if p.endswith(".py")
]


@contextlib.contextmanager
def temp_benchmark(
        objective=None, datasets=None,
        solvers=None, config=None
):
    if objective is None:
        objective = dummy_objective
    if solvers is None:
        solvers = dummy_solvers
    if datasets is None:
        datasets = dummy_datasets

    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        (temp_path / "solvers").mkdir()
        (temp_path / "datasets").mkdir()
        with open(temp_path / "objective.py", "w") as f:
            f.write(objective)
        for idx, dataset in enumerate(datasets):
            with open(temp_path / "solvers" / f"solver_{idx}.py", "w") as f:
                f.write(dataset)

        for idx, solver in enumerate(solvers):
            with open(temp_path / "datasets" / f"dataset_{idx}.py", "w") as f:
                f.write(solver)

        if config is not None:
            with open(temp_path / "config.yml", "w") as f:
                f.write(solver)

        yield Benchmark(temp_path)
