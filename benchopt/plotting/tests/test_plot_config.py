import pytest
from unittest.mock import patch

from benchopt.cli.main import run
from benchopt.utils.temp_benchmark import temp_benchmark

from benchopt.tests.utils import CaptureCmdOutput


@pytest.mark.parametrize(
    "config, expected_warning",
    [
        (
            """
            plot_configs:
              my-view:
                scale: log
            """,
            "has no 'plot_kind' specified",
        ),
        (
            """
            plot_configs:
              my-view:
                plot_kind: not_a_kind
            """,
            "invalid plot_kind",
        ),
        (
            """
            plot_configs:
              my-view:
                plot_kind: objective_curve
                objective_curve_unknown_option: true
            """,
            "has invalid options",
        ),
    ],
    ids=["no_plot_kind", "invalid_plot_kind", "invalid_plot_options"]
)
def test_plot_config_view_validation_warnings(config, expected_warning):
    with temp_benchmark(config=config) as bench:
        with CaptureCmdOutput() as out:
            with pytest.warns(UserWarning, match=expected_warning):
                run(
                    f"{bench.benchmark_dir} -n 1 -r 1 --no-display".split(),
                    standalone_mode=False
                )

        out.check_output("Rendering benchmark results", repetition=1)


@pytest.mark.parametrize("key", ["plots", "hidden_plots"])
def test_plot_benchmark_invalid_kind_raises(key):
    config = f"""
    {key}:
      - not_a_plot_kind
    """

    with temp_benchmark(config=config) as bench:
        # `run` catches plotting errors and prints them.
        with CaptureCmdOutput(exit=1) as out:
            run(
                f"{bench.benchmark_dir} -n 1 -r 1 --no-display".split(),
                standalone_mode=False
            )
        out.check_output("Invalid plot kind 'not_a_plot_kind'", repetition=1)
        out.check_output(f"in the {bench.name} section", repetition=1)
        out.check_output("config. Available kinds", repetition=1)


def test_hidden_plots():
    # Names are lowercased, so 'BoxPlot' and 'Table' match the plot kinds.
    config = """
    hidden_plots:
      - BoxPlot
      - Table
    """

    with temp_benchmark(config=config) as bench:
        with CaptureCmdOutput():
            with patch("benchopt.plotting.plot_benchmark_html") as html:
                run(
                    f"{bench.benchmark_dir} -n 1 -r 1 --no-display".split(),
                    standalone_mode=False
                )
        plots = html.call_args.args[2]["plots"]
        assert "boxplot" not in plots and "table" not in plots
        assert "objective_curve" in plots
