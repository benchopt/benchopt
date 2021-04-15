from pathlib import Path
from benchopt.benchmark import Benchmark

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
