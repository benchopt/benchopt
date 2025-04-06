import os
import inspect
import tempfile
import contextlib

from pathlib import Path

from benchopt.benchmark import Benchmark
from benchopt.tests import DUMMY_BENCHMARK_PATH
from benchopt.mini import get_mini_benchmark


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
    config: str | None (default=None)
        Content of configuration file for running the Benchmark. If None,
        no config file is created.
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
            with open(temp_path / "config.yml", "w", encoding='utf-8') as f:
                f.write(config)

        if benchmark_utils is not None:
            benchmark_utils_dir = (temp_path / "benchmark_utils")
            benchmark_utils_dir.mkdir()
            (benchmark_utils_dir / "__init__.py").touch()
            for fname, content in benchmark_utils.items():
                fname = (benchmark_utils_dir / fname).with_suffix(".py")
                with open(fname, "w") as f:
                    f.write(inspect.cleandoc(content))

        yield Benchmark(temp_path)


@contextlib.contextmanager
def temp_mini_benchmark(
        mini_bench=None, config=None,
        benchmark_utils=None
):
    """Create Benchmark in a temporary folder, for test purposes.

    Parameters
    ----------
    mini_bench: str | None (default=None)
        Content of the mini benchmark file. If None, defaults to mini benchmark
        defined inside this context manager
    config: str | None (default=None)
        Content of configuration file for running the Benchmark. If None,
        no config file is created.
    benchmark_utils: dict(fname->str) | None (default=None)
    """
    if mini_bench is None:
        benchmark = """from benchopt.mini import solver, dataset, objective
            import jax
            
            @dataset(
                size=100,
                random_state=0
            )
            def simulated(size, random_state):
                key = jax.random.PRNGKey(random_state)
                key, subkey = jax.random.split(key)
                X = jax.random.normal(key, (size,))
                return dict(X=X)
            
            
            @solver(
                name="Solver 1",
                lr=[1e-2, 1e-3]
            )
            def solver1(n_iter, X, lr):
                beta = X
                for i in range(n_iter):
                    beta -= lr * beta
            
                return dict(beta=beta)
            
            
            @objective(name="Benchmark HVP")
            def evaluate(beta):
                return dict(value=(0.5 * beta.dot(beta)).item())
        """
    else:
        benchmark = mini_bench

    with tempfile.TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        with open(temp_path / "benchmark.py", "w", encoding='utf-8') as f:
            f.write(inspect.cleandoc(benchmark))

        if config is not None:
            with open(temp_path / "config.yml", "w", encoding='utf-8') as f:
                f.write(config)

        if benchmark_utils is not None:
            benchmark_utils_dir = (temp_path / "benchmark_utils")
            benchmark_utils_dir.mkdir()
            (benchmark_utils_dir / "__init__.py").touch()
            for fname, content in benchmark_utils.items():
                fname = (benchmark_utils_dir / fname).with_suffix(".py")
                with open(fname, "w") as f:
                    f.write(inspect.cleandoc(content))

        yield get_mini_benchmark(temp_path / "benchmark.py")
