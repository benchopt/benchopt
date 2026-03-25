import re
import pytest

from benchopt.helpers.run_examples import (
    ExampleBenchmark,
    HTMLResultPage,
    benchopt_cli,
)

from benchopt.utils.temp_benchmark import temp_benchmark


def test_run_example_benchmark(no_debug_log):
    """Test that an example benchmark runs end-to-end."""
    pytest.importorskip("rich")

    with temp_benchmark() as bench:
        output = benchopt_cli(f"run {bench.benchmark_dir} -n 2 -r 3")

    assert isinstance(output, HTMLResultPage)

    # Check that the command is correctly emulated
    assert bench.benchmark_dir.stem in output.cmd, output.cmd
    assert "-n 2" in output.cmd, output.cmd
    assert "-r 3" in output.cmd, output.cmd

    out = output.output_html
    # Check that the \r are correctly emulated in html output
    assert len(re.findall(r"\|--test-solver:", out)) == 2, out


def test_example_benchmark_tabs_and_mutation():
    solver = """
    from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = 'python-gd'
        def set_objective(self, X): self.X = X
        def run(self, _): self.X_hat = self.X
        def get_result(self): return dict(X_hat=self.X_hat)
    """

    benchmark = ExampleBenchmark(solvers=solver)
    try:
        html = benchmark._repr_html_()
        assert "objective.py" not in html
        assert "datasets/simulated.py" not in html
        assert "solvers/python_gd.py" in html

        updated = benchmark.update(
            solvers=[solver.replace("name = 'python-gd'", "name = 'julia'")],
            extra_files={"julia_gd.jl": "function gd()\nend"},
        )

        html = updated._repr_html_()
        assert "solvers/julia.py" in html
        assert "julia_gd.jl" in html
        assert "solvers/python_gd.py" not in html
    finally:
        benchmark.close()


def test_example_benchmark_from_existing_benchmark():
    benchmark = ExampleBenchmark(base="minimal_benchmark")
    try:
        html = benchmark._repr_html_()
        assert "objective.py" in html
        assert "datasets/simulated.py" in html
        assert "solvers/gd.py" in html
    finally:
        benchmark.close()


def test_example_benchmark_run(no_debug_log):
    pytest.importorskip("rich")

    objective = """
    import numpy as np
    from benchopt import BaseObjective

    class Objective(BaseObjective):
        name = 'MSE'
        def set_data(self, X): self.X = X
        def get_objective(self): return dict(X=self.X)
        def evaluate_result(self, X_hat):
            mse = np.mean((self.X - X_hat) ** 2)
            return dict(value=mse, mse=mse)
        def get_one_result(self): return dict(X_hat=np.zeros_like(self.X))
    """
    dataset = """
    import numpy as np
    from benchopt import BaseDataset

    class Dataset(BaseDataset):
        name = 'simulated'
        def get_data(self): return dict(X=np.ones((3, 2)))
    """
    solver = """
    import numpy as np
    from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = 'Python-GD'
        sampling_strategy = 'iteration'
        parameters = {'lr': [1e-1]}
        def set_objective(self, X):
            self.X = X
            self.X_hat = np.zeros_like(X)
        def run(self, n_iter):
            for _ in range(n_iter):
                self.X_hat -= self.lr * (self.X_hat - self.X)
        def get_result(self): return dict(X_hat=self.X_hat)
    """

    benchmark = ExampleBenchmark(
        objective=objective,
        datasets={"simulated.py": dataset},
        solvers={"python_gd.py": solver},
    )
    try:
        output = benchopt_cli(f"run {benchmark.benchmark_dir} -n 2 -r 1")
        assert isinstance(output, HTMLResultPage)
        assert benchmark.benchmark_dir.stem in output.cmd
    finally:
        benchmark.close()
