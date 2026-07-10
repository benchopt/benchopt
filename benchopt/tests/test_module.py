import sys
from subprocess import check_output

from benchopt.utils.temp_benchmark import temp_benchmark

from benchopt.tests.utils.capture_cmd_output import BenchoptCmdOutputProcessor


def test_run_benchopt_module(no_debug_log):
    # Check that benchopt can be called as a python module, as
    # $ python -m benchopt run

    # Create a temporary benchmark directory
    with temp_benchmark() as tmp_dir:
        output = check_output([
            sys.executable, "-m", "benchopt", "run", tmp_dir.benchmark_dir,
            "-d", "test-dataset", '-n', "0", "--no-plot"
        ],).decode("utf-8")
        output = BenchoptCmdOutputProcessor(output)

    output.check_output('test-dataset', repetition=1)
    output.check_output('simulated', repetition=0)
    output.check_output('test-objective', repetition=1)
    output.check_output("test-solver:", repetition=2)
    output.check_output(r'Python-PGD\[step_size=1.5\]:', repetition=0)
    assert len(output.result_files) == 1
