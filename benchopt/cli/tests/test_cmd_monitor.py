import click
import pytest

from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.tests.utils import CaptureCmdOutput

from benchopt.cli.main import monitor, run


def test_monitor(tmp_path, monkeypatch):
    monkeypatch.setenv("BENCHOPT_RUNS_DIR", str(tmp_path))

    with CaptureCmdOutput() as out:
        monitor([], "benchopt", standalone_mode=False)
    out.check_output("No benchmark run found")

    with temp_benchmark() as bench:
        with CaptureCmdOutput():
            run([str(bench.benchmark_dir), "-n", "1", "-r", "1",
                 "--no-plot", "--output", "monitored_run"],
                "benchopt", standalone_mode=False)

    # Without a terminal, the runs are listed rather than picked.
    with CaptureCmdOutput() as out:
        monitor([], "benchopt", standalone_mode=False)
    out.check_output("monitored_run")
    out.check_output("done")

    # A run is selected by `last` or the start of its name, and its
    # results are printed.
    for name in ["last", "monitored"]:
        with CaptureCmdOutput() as out:
            monitor([name], "benchopt", standalone_mode=False)
        out.check_output("Results")
        out.check_output("simulated")
        out.check_output("done · monitored_run")

    with pytest.raises(click.BadParameter, match="No run matching"):
        monitor(["unknown"], "benchopt", standalone_mode=False)


def test_monitor_errors(tmp_path, monkeypatch, no_debug_log):
    from rich.console import Console
    from benchopt.utils.monitor import _errors, _Pager, load_runs
    from benchopt.utils.monitor import read_results

    monkeypatch.setenv("BENCHOPT_RUNS_DIR", str(tmp_path))
    solver = """from benchopt.utils.temp_benchmark import TempSolver
        class Solver(TempSolver):
            name = "failing-solver"
            def run(self, n_iter): raise ValueError("Intentional Error")
    """
    with temp_benchmark(solvers=[solver]) as bench:
        with CaptureCmdOutput(exit=1):
            run([str(bench.benchmark_dir), "-n", "1", "-r", "1",
                 "--no-plot", "-s", "failing-solver"],
                "benchopt", standalone_mode=False)

    # The traceback of the failed run is kept, to be shown on a screen.
    (snapshot,) = load_runs()
    errors = _errors(snapshot, read_results(snapshot)[0])
    assert "failing-solver" in errors
    assert 'ValueError: Intentional Error' in errors

    console = Console(width=80, height=10, record=True)
    pager = _Pager("Errors", errors, top=len(errors))
    console.print(pager.render(console))
    assert "Intentional Error" in console.export_text()
