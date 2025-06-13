import sys
from subprocess import check_output

from benchopt.utils.temp_benchmark import temp_benchmark

from benchopt.tests import SELECT_ONE_PGD
from benchopt.tests import SELECT_ONE_SIMULATED
from benchopt.tests import SELECT_ONE_OBJECTIVE
from benchopt.tests.utils.capture_run_output import BenchoptRunOutputProcessor


def test_run_benchopt_module(no_debug_log):
    # Check that benchopt can be called as a python module, as
    # $ python -m benchopt run

    # Create a temporary benchmark directory
    with temp_benchmark() as tmp_dir:
        output = check_output([
            sys.executable, "-m", "benchopt", "run", tmp_dir.benchmark_dir,
            "-d", SELECT_ONE_SIMULATED, "-o", SELECT_ONE_OBJECTIVE, '-n', "1",
            "-s", SELECT_ONE_PGD, "--no-plot"
        ],).decode("utf-8")
        output = BenchoptRunOutputProcessor(output)

    output.check_output('Simulated', repetition=1)
    output.check_output('Dummy Sparse Regression', repetition=1)
    output.check_output(r'Python-PGD\[step_size=1\]:')
    output.check_output(r'Python-PGD\[step_size=1.5\]:', repetition=0)
    assert len(output.result_files) == 1
