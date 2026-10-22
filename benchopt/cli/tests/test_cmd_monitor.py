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
