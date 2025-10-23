import sys
import yaml
import inspect
import tempfile
import contextlib

from pathlib import Path

from benchopt.benchmark import Benchmark


DEFAULT_OBJECTIVE = """from benchopt import BaseObjective

class Objective(BaseObjective):
    name = "test-objective"
    def set_data(self, X, y): pass
    def get_one_result(self): return dict(beta=None)
    def evaluate_result(self, beta): return 1.
    def get_objective(self): return dict(X=None, y=None, lmbd=None)
"""

IDX_BENCHMARK = 0

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
        objective=None, datasets=None, solvers=None, plots=None,
        config=None, benchmark_utils=None, extra_files=None
):
    """Create Benchmark in a temporary folder, for test purposes.

    Parameters
    ----------
    objective: str | None (default=None)
        Content of the objective.py file. If None, defaults to
        ``DEFAULT_OBJECTIVE``.
    datasets: str | list of str | None (default=None)
        Content of the dataset.py file(s). If None, defaults to
        ``DEFAULT_DATASETS``.
    solvers: str | list of str | dict of str | None (default=None)
        Content of the solver.py file(s). If None, defaults to
        ``DEFAULT_SOLVERS``.
    plots: str | list of str | dict of str | None (default=None)
        Content of the plot.py file(s). If None, no plot file is created.
    config: str | dict(fname->content) | None (default=None)
        Configuration files for running the Benchmark. If only one str is
        passed, this creates only one `config.yml` file. If None, no config
        file is created. If a dict, the content can either be a str or a dict,
        which will be written as a YAML file.
    benchmark_utils: dict(fname->str) | None (default=None)
        Content of the benchmark_utils module.
    extra_files: dict(fname->str) | None (default=None)
        Additional files to be added to the benchmark directory. If None,
        no extra files are created.
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
    if isinstance(plots, str):
        plots = [plots]

    if isinstance(solvers, list):
        solvers = {f"solver_{idx}.py": s for idx, s in enumerate(solvers)}
    else:
        solvers = {**DEFAULT_SOLVERS, **solvers}

    if isinstance(datasets, list):
        datasets = {f"dataset_{idx}.py": d for idx, d in enumerate(datasets)}
    else:
        datasets = {**DEFAULT_DATASETS, **datasets}

    if isinstance(plots, list):
        plots = {f"plot_{idx}.py": p for idx, p in enumerate(plots)}

    global IDX_BENCHMARK
    idx = IDX_BENCHMARK
    IDX_BENCHMARK += 1

    with tempfile.TemporaryDirectory(
            prefix="temp_benchmarks", suffix="", dir="."
    ) as tempdir:
        temp_path = Path(tempdir) / f"bench_{idx}"
        temp_path.mkdir()
        (temp_path / "solvers").mkdir()
        (temp_path / "datasets").mkdir()
        (temp_path / "plots").mkdir()
        with open(temp_path / "objective.py", "w", encoding='utf-8') as f:
            f.write(inspect.cleandoc(objective))
        for fname, content in solvers.items():
            fname = temp_path / "solvers" / fname
            fname.write_text(inspect.cleandoc(content), encoding='utf-8')

        for fname, content in datasets.items():
            fname = temp_path / "datasets" / fname
            fname.write_text(inspect.cleandoc(content), encoding='utf-8')

        if plots is not None:
            for fname, content in plots.items():
                fname = temp_path / "plots" / fname
                fname.write_text(inspect.cleandoc(content), encoding='utf-8')

        if config is not None:
            if not isinstance(config, dict):
                assert isinstance(config, str), "config must be a dict or str"
                config = {"config.yml": config}
            for fname, content in config.items():
                if isinstance(content, dict):
                    # If content is a dict, write it as YAML
                    content = yaml.dump(content)
                else:
                    content = inspect.cleandoc(content)
                config_path = (temp_path / fname).with_suffix(".yml")
                config_path.write_text(content, encoding='utf-8')

        if benchmark_utils is not None:
            benchmark_utils_dir = (temp_path / "benchmark_utils")
            benchmark_utils_dir.mkdir()
            (benchmark_utils_dir / "__init__.py").touch()
            for fname, content in benchmark_utils.items():
                fname = (benchmark_utils_dir / fname).with_suffix(".py")
                fname.parent.mkdir(exist_ok=True, parents=True)
                fname.write_text(inspect.cleandoc(content), encoding='utf-8')

        if extra_files is not None:
            assert isinstance(extra_files, dict), "extra_files must be a dict"
            for fname, content in extra_files.items():
                (temp_path / fname).write_text(
                    inspect.cleandoc(content), encoding='utf-8'
                )

        bench = Benchmark(temp_path)
        yield bench

        # to avoid border effects, remove the benchmark directory
        to_del = [
            m for m in sys.modules
            if "benchmark_utils" in m or "benchopt_benchmarks" in m
        ]
        for m in to_del:
            sys.modules.pop(m)
