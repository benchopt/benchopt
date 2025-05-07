import os
import sys
import inspect
import tempfile
import contextlib

from pathlib import Path

from benchopt.benchmark import Benchmark
from benchopt.tests import DUMMY_BENCHMARK_PATH


dummy_objective = (DUMMY_BENCHMARK_PATH / 'objective.py').read_text()

dummy_solvers = [
    (DUMMY_BENCHMARK_PATH / "solvers" / p).read_text()
    for p in os.listdir(DUMMY_BENCHMARK_PATH / "solvers")
    if p.endswith(".py") and not p.startswith("template_")
]

dummy_datasets = [
    (DUMMY_BENCHMARK_PATH / "datasets" / p).read_text()
    for p in os.listdir(DUMMY_BENCHMARK_PATH / "datasets")
    if p.endswith(".py") and not p.startswith("template_")
]

DEFAULT_OBJECTIVE = """from benchopt import BaseObjective

class Objective(BaseObjective):
    name = "test"
    def set_data(self, X, y): pass
    def get_one_result(self): return dict(beta=None)
    def evaluate_result(self, beta): return 1
    def get_objective(self): return dict(X=None, y=None, lmbd=None)
"""

DEFAULT_DATASETS = {
    'test_dataset.py': """from benchopt import BaseDataset

        class Dataset(BaseDataset):
            name = "test-dataset"
            def get_data(self): return dict(X=None, y=None)
    """,
    'simulated.py': """from benchopt import BaseDataset

        class Dataset(BaseDataset):
            name = "simulated"
            def get_data(self): return dict(X=None, y=None)
    """
}
DEFAULT_SOLVERS = {
    'test_solver.py': """from benchopt import BaseSolver

        class Solver(BaseSolver):
            name = "test-solver"
            def set_objective(self, X, y, lmbd): pass
            def run(self, _): pass
            def get_result(self): return dict(beta=None)
    """
}


@contextlib.contextmanager
def temp_benchmark(
        objective=None, datasets=None, solvers=None, config=None,
        benchmark_utils=None
):
    """Create Benchmark in a temporary folder, for test purposes.

    Parameters
    ----------
    objective: str | None (default=None)
        Content of the objective.py file. If None, defaults to objective of
        ``benchopt.tests.DUMMY_BENCHMARK``.
    datasets: str | list of str | None (default=None)
        Content of the dataset.py file(s). If None, defaults to datasets of
        ``benchopt.tests.DUMMY_BENCHMARK``.
    solvers: str | list of str | dict of str | None (default=None)
        Content of the solver.py file(s). If None, defaults to solvers of
        ``benchopt.tests.DUMMY_BENCHMARK``.
    config: str | None (default=None)
        Content of configuration file for running the Benchmark. If None,
        no config file is created.
    benchmark_utils: dict(fname->str) | None (default=None)
    """
    if objective is None:
        objective = DEFAULT_OBJECTIVE
    if solvers is None:
        solvers = DEFAULT_SOLVERS
    if datasets is None:
        datasets = DEFAULT_DATASETS

    if isinstance(datasets, str):
        datasets = [datasets]
    if isinstance(solvers, str):
        solvers = [solvers]

    if isinstance(solvers, list):
        solvers = {f"solver_{idx}.py": s for idx, s in enumerate(solvers)}
    else:
        solvers = {**DEFAULT_SOLVERS, **solvers}

    if isinstance(datasets, list):
        datasets = {f"dataset_{idx}.py": d for idx, d in enumerate(datasets)}
    else:
        datasets = {**DEFAULT_DATASETS, **datasets}

    # Make sure the benchmark_utils is reloaded
    to_del = [m for m in sys.modules if "benchmark_utils" in m or "benchopt_benchmarks" in m]
    for m in to_del:
        sys.modules.pop(m)

    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        (temp_path / "solvers").mkdir()
        (temp_path / "datasets").mkdir()
        with open(temp_path / "objective.py", "w", encoding='utf-8') as f:
            f.write(inspect.cleandoc(objective))
        for fname, content in solvers.items():
            fname = temp_path / "solvers" / fname
            with open(fname, "w", encoding='utf-8') as f:
                f.write(inspect.cleandoc(content))

        for fname, content in datasets.items():
            fname = temp_path / "datasets" / fname
            with open(fname, "w", encoding='utf-8') as f:
                f.write(inspect.cleandoc(content))

        if config is not None:
            with open(temp_path / "config.yml", "w", encoding='utf-8') as f:
                f.write(config)

        if benchmark_utils is not None:
            benchmark_utils_dir = (temp_path / "benchmark_utils")
            benchmark_utils_dir.mkdir()
            (benchmark_utils_dir / "__init__.py").touch()
            for fname, content in benchmark_utils.items():
                fname = (benchmark_utils_dir / fname).with_suffix(".py")
                fname.parent.mkdir(exist_ok=True, parents=True)
                with open(fname, "w", encoding='utf-8') as f:
                    f.write(inspect.cleandoc(content))

        yield Benchmark(temp_path)
