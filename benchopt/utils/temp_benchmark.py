import os
import tempfile
import contextlib

from pathlib import Path

from benchopt.benchmark import Benchmark

dummy_objective = """
"""

dummy_datasets = ("""
""",)

dummy_solver = ("""
""",)

@contextlib.contextmanager
def temp_benchmark(
        objective=dummy_objective, datasets=dummy_datasets,
        solvers=dummy_solver, config=None):
    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        os.mkdir(temp_path / "solvers")
        os.mkdir(temp_path / "datasets")
        with open(temp_path / "objective.py", "w") as f:
            f.write(objective)
        for idx, dataset in enumerate(datasets):
            with open(temp_path / "solvers" / f"{idx}.py", "w") as f:
                f.write(dataset)

        for idx, solver in enumerate(solvers):
            with open(temp_path / "datasets" / f"{idx}.py", "w") as f:
                f.write(solver)

        if config is not None:
            with open(temp_path / "config.yml", "w") as f:
                f.write(solver)

        yield Benchmark(temp_path)
