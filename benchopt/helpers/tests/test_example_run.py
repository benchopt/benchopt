import re
import pytest
import tempfile
import webbrowser
from pathlib import Path

from benchopt.helpers.run_examples import (
    ExampleBenchmark,
    HTMLCmdOutput,
    benchopt_cli,
    SPHINX_GALLERY_CTX
)

from benchopt.utils.temp_benchmark import temp_benchmark

# Skip this module is rich is not installed
pytest.importorskip("rich")


def test_run_example_benchmark(no_debug_log, monkeypatch):
    """Test that an example benchmark runs end-to-end."""

    with monkeypatch.context() as m, tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)

        # Mock the path iterator to store the HTML result files in a temporary
        # directory for testing.
        open_call = []
        m.setitem(SPHINX_GALLERY_CTX, "paths", iter(
            f"auto_examples/images/output_{i}.png" for i in range(1)
        ))
        m.setitem(SPHINX_GALLERY_CTX, "build_dir", tmp_dir)
        m.setattr(webbrowser, "open", lambda *x: open_call.append(x))

        # Create a temporary benchmark and run it with the CLI.
        with temp_benchmark() as bench:
            output = benchopt_cli(f"run {bench.benchmark_dir} -n 2 -r 3")

        assert isinstance(output, HTMLCmdOutput)

        # Check that the command is correctly emulated
        assert bench.benchmark_dir.stem in output.cmd, output.cmd
        assert "-n 2" in output.cmd, output.cmd
        assert "-r 3" in output.cmd, output.cmd

        out = output.output_html
        # Check that the \r are correctly emulated in html output
        assert len(re.findall(r"\|--test-solver:", out)) == 2, out

        # Check that the HTML result is correctly saved
        output._repr_html_()  # Check that the HTML can be generated
        assert (tmp_dir / "html_results" / "output_0.html").exists()

        assert len(open_call) == 0, "Calling in sphinx should not call display"


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


def test_example_benchmark_run(no_debug_log, monkeypatch):

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
    with monkeypatch.context() as m:
        open_call = []
        m.setattr(webbrowser, "open", lambda *x: open_call.append(x))

        output = benchopt_cli(f"run {benchmark.benchmark_dir} -n 2 -r 1")
        assert isinstance(output, HTMLCmdOutput)
        assert benchmark.benchmark_dir.stem in output.cmd

        # check that the display was correctly called
        assert len(open_call) == 1, "HTML result should be opened in the call"
        assert open_call[0][0].startswith("file://")
        assert open_call[0][0].endswith(".html")

    updated = benchmark.update(objective=objective.replace("MSE", "#TEST#"))
    html = updated._repr_html_()
    assert "objective.py" in html
    assert "#TEST#" in html
    assert "#TEST#" in (benchmark.benchmark_dir / "objective.py").read_text()


def test_example_file_detection(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        fres = "test.html"

        def run(*a, **k):
            (temp_dir / fres).touch()
            print(f"Writing result to {temp_dir / fres}")
        with monkeypatch.context() as m:
            m.setitem(globals(), "__file__", f"{temp_dir}/run_solver.py")
            m.setattr("benchopt.cli.benchopt", run)
            benchopt_cli("run test")
            assert (temp_dir / "output_solver" / fres).exists(), (
                list(temp_dir.rglob("*"))
            )


@pytest.mark.parametrize("cmd, injected", [
    ("run fake_bench -n 2", "--no-display"),
    ("run fake_bench --no-display -n 2", "--no-display"),
    ("install fake_bench -s julia-gd", "--yes"),
    ("install fake_bench --yes -s julia-gd", "--yes"),
])
def test_benchopt_cli_injects_sphinx_options(cmd, injected, monkeypatch):
    recorded = []

    def fake_benchopt(cmd_parts, standalone_mode=False):
        recorded.append(list(cmd_parts))
        return None

    with monkeypatch.context() as m:
        m.setattr("benchopt.cli.benchopt", fake_benchopt)

        # First call: as in sphinx, with injection
        m.setitem(SPHINX_GALLERY_CTX, "paths", iter([]))
        benchopt_cli(cmd)
        assert len(recorded) == 1
        recorded_cmd = recorded[-1]
        assert injected in recorded_cmd
        assert recorded_cmd.count(injected) == 1

        # First call: not in sphinx, no injection
        m.delitem(SPHINX_GALLERY_CTX, "paths")
        recorded.clear()
        benchopt_cli(cmd)
        assert len(recorded) == 1
        recorded_cmd = recorded[-1]
        assert injected not in recorded_cmd or injected in cmd


def test_example_benchmark_invalid_base_path():
    with pytest.raises(ValueError, match="Could not find benchmark"):
        ExampleBenchmark(base="benchmark_does_not_exist_for_tests")


def test_example_benchmark_missing_solver_name():
    solver_without_name = """
    from benchopt import BaseSolver

    class Solver(BaseSolver):
        def set_objective(self, X):
            self.X = X
        def run(self, _):
            self.X_hat = self.X
        def get_result(self):
            return dict(X_hat=self.X_hat)
    """

    with pytest.raises(ValueError, match="Could not extract name"):
        ExampleBenchmark(solvers=solver_without_name)
