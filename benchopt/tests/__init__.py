import re

from pathlib import Path
from benchopt.benchmark import Benchmark
from benchopt.utils.stream_redirection import SuppressStd

# Default benchmark
TEST_BENCHMARK_DIR = Path(__file__).parent / 'test_benchmarks'
DUMMY_BENCHMARK_PATH = TEST_BENCHMARK_DIR / 'dummy_benchmark'

# Pattern to select specific datasets or solvers.
SELECT_ONE_SIMULATED = r'simulated*500*rho=0\]'
SELECT_ONE_PGD = r'python-pgd*step_size=1\]'

try:
    DUMMY_BENCHMARK = Benchmark(DUMMY_BENCHMARK_PATH)
    TEST_OBJECTIVE = DUMMY_BENCHMARK.get_benchmark_objective()
    TEST_SOLVER = [s for s in DUMMY_BENCHMARK.list_benchmark_solvers()
                   if s.name == "Test-Solver"][0]
    TEST_DATASET = [d for d in DUMMY_BENCHMARK.list_benchmark_datasets()
                    if d.name == "Test-Dataset"][0]
except Exception:
    DUMMY_BENCHMARK = None
    TEST_OBJECTIVE = None
    TEST_SOLVER = None
    TEST_DATASET = None


class CaptureRunOutput(object):
    """Context to capture run cmd output and files.
    """

    def __init__(self):
        self.out = SuppressStd()
        self.output = None
        self.result_files = []

    def __enter__(self):
        self.output = None
        self.result_files = []

        # Redirect the stdout/stderr fd to temp file
        self.out.__enter__()
        return self

    def __exit__(self, exc_class, value, traceback):
        self.out.__exit__(exc_class, value, traceback)
        self.output = self.out.output

        # Make sure to delete all the result that created by the run command.
        self.result_files = re.findall(
            r'Saving result in: (.*\.csv)', self.output
        )
        if len(self.result_files) >= 1:
            for result_file in self.result_files:
                Path(result_file).unlink()

        # If there was an exception, display the output
        if exc_class is not None:
            print(self.output)

    def check_output(self, pattern, repetition=None):
        matches = re.findall(pattern, self.output)
        if repetition is None:
            assert len(matches) > 0, self.output
        else:
            assert len(matches) == repetition, self.output
