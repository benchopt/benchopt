import pytest

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
def test_plot_config_view_validation_warnings(no_debug_log, config, expected_warning):
    with temp_benchmark(config=config) as bench:
        with CaptureCmdOutput() as out:
            with pytest.warns(UserWarning, match=expected_warning):
                run(
                    f"{bench.benchmark_dir} -n 1 -r 1 --no-display".split(),
                    standalone_mode=False
                )

        out.check_output("Rendering benchmark results", repetition=1)


def test_plot_benchmark_invalid_kind_raises(no_debug_log):
    config = """
    plots:
      - not_a_plot_kind
    """

    with temp_benchmark(config=config) as bench:
        with CaptureCmdOutput(exit=1):
            with pytest.raises(
                ValueError, match="Invalid plot kind 'not_a_plot_kind'"
            ):
                run(
                    f"{bench.benchmark_dir} -n 1 -r 1 --no-display".split(),
                    standalone_mode=False
                )
