import re
import pytest

from benchopt.helpers.run_examples import benchopt_run, HTMLResultPage

from benchopt.utils.temp_benchmark import temp_benchmark


def test_run_example_benchmark(no_debug_log):
    """Test that an example benchmark runs end-to-end."""
    pytest.importorskip("rich")

    with temp_benchmark() as bench:
        output = benchopt_run(benchmark_dir=bench.benchmark_dir, n=2, r=3)

    assert isinstance(output, HTMLResultPage)

    # Check that the command is correctly emulated
    assert bench.benchmark_dir.stem in output.cmd, output.cmd
    assert "-n 2" in output.cmd, output.cmd
    assert "-r 3" in output.cmd, output.cmd

    out = output.output_html
    # Check that the \r are correctly emulated in html output
    assert len(re.findall(r"\|--test-solver:", out)) == 2, out
