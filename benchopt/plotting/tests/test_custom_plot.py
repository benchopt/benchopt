import pytest

from benchopt.cli.main import run
from benchopt.utils.temp_benchmark import temp_benchmark

from benchopt.tests.utils import CaptureCmdOutput


def test_custom_plot(no_debug_log):
    plot = """from benchopt import BasePlot

    class Plot(BasePlot):
        name = "Custom plot 1"
        type = "scatter"
        dropdown = {}

        def plot(self, df):
            return [
                {
                    "x": [],
                    "y": [],
                    "color": "blue",
                    "marker": "circle",
                    "label": "label",
                }
            ]

        def get_metadata(self, df):
            return {
                "title": "Example plot",
                "xlabel": "custom time",
                "ylabel": "custom objective value",
            }
    """

    with temp_benchmark(plots=plot) as bench:
        with CaptureCmdOutput() as out:
            run([str(bench.benchmark_dir),
                 *'-n 1 -r 1 --no-display'
                 .split()], standalone_mode=False)

        out.check_output("Rendering benchmark results", repetition=1)


def test_custom_plot_errors(no_debug_log):  # TODO improve error checks
    plot = """from benchopt import BasePlot

    class Plot(BasePlot):
        name = 'Custom plot 1'
        type = 'scatter'
        dropdown = {}

        def plot(self, df):
            return [
                {
                    "x": [],
                    "y": [],
                    "color": "blue",
                    "marker": "circle",
                    "label": "label",
                }
            ]

        def get_metadata(self, df):
            return {
                "title": "Example plot",
                "xlabel": "custom time",
                "ylabel": "custom objective value",
            }
    """

    error_plot = plot.replace("type = 'scatter'", "")
    with temp_benchmark(plots=error_plot) as bench:
        with pytest.raises(SystemExit):
            run([str(bench.benchmark_dir),
                 *'-n 1 -r 1 --no-display'
                 .split()], standalone_mode=False)

    error_plot = plot.replace("type = 'scatter'", "type = 'curving'")
    with temp_benchmark(plots=error_plot) as bench:
        with pytest.raises(SystemExit):
            run([str(bench.benchmark_dir),
                 *'-n 1 -r 1 --no-display'
                 .split()], standalone_mode=False)

    error_plot = plot.replace("dropdown = {}", "dropdown = []")
    with temp_benchmark(plots=error_plot) as bench:
        with pytest.raises(SystemExit):
            run([str(bench.benchmark_dir),
                 *'-n 1 -r 1 --no-display'
                 .split()], standalone_mode=False)

    error_plot = plot.replace("dropdown = {}", "dropdown = {'color': 'blue'}")
    with temp_benchmark(plots=error_plot) as bench:
        with pytest.raises(SystemExit):
            run([str(bench.benchmark_dir),
                 *'-n 1 -r 1 --no-display'
                 .split()], standalone_mode=False)

    error_plot = plot.replace("dropdown = {}", "dropdown = {'color': []}")
    with temp_benchmark(plots=error_plot) as bench:
        with pytest.raises(SystemExit):
            run([str(bench.benchmark_dir),
                 *'-n 1 -r 1 --no-display'
                 .split()], standalone_mode=False)

    error_plot = plot.replace(
        "dropdown = {}",
        "dropdown = {'color': ['blue']}"
    )
    with temp_benchmark(plots=error_plot) as bench:
        with pytest.raises(SystemExit):
            run([str(bench.benchmark_dir),
                 *'-n 1 -r 1 --no-display'
                 .split()], standalone_mode=False)
