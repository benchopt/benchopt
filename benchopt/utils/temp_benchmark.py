import os
import tempfile
import contextlib

from pathlib import Path

from benchopt.benchmark import Benchmark


# default params
dummy_objective = """
"""

dummy_datasets = ("""
""",)

dummy_solver = ("""
""",)

# example
datasets = [
    (
        "from benchopt import BaseDataset\n"
        "class Dataset(BaseDataset):\n"
        "    name = 'dummy-dataset'\n"
        "    def __init__(self, param=1.):\n"
        "        self.param = param\n"
        "    def get_data(self):\n"
        "        return dict(a=1, b=1)\n"
    ),
]

solvers = [
    (
        "from benchopt import BaseSolver, safe_import_context\n"
        "with safe_import_context() as import_ctx_wrong_name:\n"
        "   import numpy as np\n"
        "class Solver(BaseSolver):\n"
        "   name = 'test_import_ctx'\n"
        "   def set_objective(self, a, b):\n"
        "       self.a, self.b = a, b\n"
        "   def run(self, n_iter):\n"
        "       return -n_iter / 1000\n"
    )
]


objective = (
    "from benchopt import BaseObjective\n"
    "import numpy as np\n"
    "class Objective(BaseObjective):\n"
    "   def set_data(self, a, b):\n"
    "       self.a, self.b = a, b\n"
    "   def get_objective(self):\n"
    "       return dict(a=self.a, b=self.b)\n"
    "   def compute(self, x):\n"
    "       return np.exp(x)\n"
)


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
