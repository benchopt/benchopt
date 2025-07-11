import os
import yaml
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
    solvers: str | list of str | None (default=None)
        Content of the solver.py file(s). If None, defaults to solvers of
        ``benchopt.tests.DUMMY_BENCHMARK``.
    config: str | dict(fname->str) | None (default=None)
        Configuration files for running the Benchmark. If only one str is
        passed, this creates only one `config.yml` file. If None, no config
        file is created.
    benchmark_utils: dict(fname->str) | None (default=None)
    """
    if objective is None:
        objective = dummy_objective
    if solvers is None:
        solvers = dummy_solvers
    if datasets is None:
        datasets = dummy_datasets

    if isinstance(datasets, str):
        datasets = [datasets]
    if isinstance(solvers, str):
        solvers = [solvers]

    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        (temp_path / "solvers").mkdir()
        (temp_path / "datasets").mkdir()
        with open(temp_path / "objective.py", "w", encoding='utf-8') as f:
            f.write(inspect.cleandoc(objective))
        for idx, solver in enumerate(solvers):
            with open(temp_path / "solvers" / f"solver_{idx}.py", "w",
                      encoding='utf-8') as f:
                f.write(inspect.cleandoc(solver))

        for idx, dataset in enumerate(datasets):
            with open(temp_path / "datasets" / f"dataset_{idx}.py", "w",
                      encoding='utf-8') as f:
                f.write(inspect.cleandoc(dataset))

        if config is not None:
            if not isinstance(config, dict):
                config = {"config.yml": config}
            for fname, content in config.items():
                if isinstance(content, dict):
                    # If content is a dict, write it as YAML
                    content = yaml.dump(content)
                config_path = (temp_path / fname).with_suffix(".yml")
                with open(config_path, "w", encoding='utf-8') as f:
                    f.write(content)

        if benchmark_utils is not None:
            benchmark_utils_dir = (temp_path / "benchmark_utils")
            benchmark_utils_dir.mkdir()
            (benchmark_utils_dir / "__init__.py").touch()
            for fname, content in benchmark_utils.items():
                fname = (benchmark_utils_dir / fname).with_suffix(".py")
                with open(fname, "w") as f:
                    f.write(inspect.cleandoc(content))

        yield Benchmark(temp_path)
