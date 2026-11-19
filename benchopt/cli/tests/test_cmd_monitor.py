import json
from time import time

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

    # `--wait` polls the run until it is over, then prints its results.
    (path,) = tmp_path.glob("*.json")
    snapshot = json.loads(path.read_text())
    path.write_text(json.dumps(dict(snapshot, finished=None, updated=time())))
    polls = []

    def sleep(_):
        polls.append(1)
        path.write_text(json.dumps(snapshot))
    monkeypatch.setattr("benchopt.utils.monitor.sleep", sleep)
    with CaptureCmdOutput() as out:
        monitor(["--wait"], "benchopt", standalone_mode=False)
    out.check_output("done · monitored_run")
    assert polls == [1]


def test_monitor_errors(tmp_path, monkeypatch, no_debug_log):
    from rich.console import Console
    from benchopt.utils.monitor import _failed, _Pager, _view, load_runs
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

    # The failed run is selected in the results, with its traceback.
    (snapshot,) = load_runs()
    console = Console(width=80, height=20, record=True)
    view = _view(snapshot, read_results(snapshot)[0], console)
    line = _failed(view)[0]
    assert line.name.endswith("failing-solver")
    assert "ValueError: Intentional Error" in line.traceback

    view._selected = 0
    console.print(view._render())
    assert "failing-solver" in console.export_text()

    pager = _Pager(line.name, line.traceback, top=len(line.traceback))
    console.print(pager.render(console))
    assert "Intentional Error" in console.export_text()

    # For agents: the tracebacks are printed, and the failure is the exit
    # code, also once the run is waited for.
    for args in [["--errors"], ["last", "--wait"]]:
        with CaptureCmdOutput(exit=1) as out:
            monitor(args, "benchopt", standalone_mode=False)
        out.check_output(r"· error [1-9]")
    out.check_output("Intentional Error", repetition=0)
    with CaptureCmdOutput(exit=1) as out:
        monitor(["--errors"], "benchopt", standalone_mode=False)
    out.check_output("ValueError: Intentional Error")
    out.check_output("Results", repetition=0)
