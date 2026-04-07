import pytest

from benchopt.cli.main import run
from benchopt.utils.temp_benchmark import temp_benchmark

from benchopt.tests.utils import CaptureCmdOutput

CUSTOM_PLOT = """from benchopt import BasePlot

    class Plot(BasePlot):
        name = "Custom plot 1"
        type = "scatter"
        options = {}

        def plot(self, df):
            return [
                {
                    "x": [],
                    "y": [],
                    "color": [0, 0, 1, 1],
                    "marker": 0,
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


def test_custom_plot_scatter(no_debug_log):

    with temp_benchmark(plots=CUSTOM_PLOT) as bench:
        with CaptureCmdOutput() as out:
            run([str(bench.benchmark_dir),
                 *'-n 1 -r 1 --no-display'
                 .split()], standalone_mode=False)

        out.check_output("Rendering benchmark results", repetition=1)


@pytest.mark.parametrize(
    "pat, replace, msg",
    [
        ("type = \"scatter\"", "", "Plot should have a `type` attribute."),
        ("type = \"scatter\"", "type = \"curving\"", "Plot type should be "),
        ("options = {}", "options = []",
         "`options` should be a dictionary"),
        ("options = {}", "options = {'color': 'blue'}",
         "The values of options should be a list or ..."),
        ("options = {}", "options = {'color': []}",
         "The values of options should be non empty"),
        ("options = {}", "options = {'color': ['blue']}",
         "should match the signature"),
    ],
    ids=[
        "no-type", "invalid-type", "options-not-dict",
        "options-values-not-list", "options-values-empty",
        "options-values-not-matching"
    ]
)
def test_custom_plot_errors(no_debug_log, pat, replace, msg):

    error_plot = CUSTOM_PLOT.replace(pat, replace)
    with temp_benchmark(plots=error_plot) as bench:
        with CaptureCmdOutput(exit=1) as out:
            run(f"{bench.benchmark_dir} -n 1 -r 1 --no-display"
                .split(), standalone_mode=False)
        out.check_output(msg)


@pytest.mark.parametrize("option", [
    'invalid', 'custom_plot_1_invalid', 'boxplot_X_axis'
])
def test_plot_config_view_validation_warnings(no_debug_log, option):
    config = f"""
    plot_configs:
        my-view:
            plot_kind: custom_plot_1
            {option}: true
    """
    with temp_benchmark(config=config, plots=CUSTOM_PLOT) as bench:
        with CaptureCmdOutput() as out:
            with pytest.warns(UserWarning, match=f"invalid options.*{option}"):
                run(
                    f"{bench.benchmark_dir} -n 1 -r 1 --no-display".split(),
                    standalone_mode=False
                )

        out.check_output("Rendering benchmark results", repetition=1)
