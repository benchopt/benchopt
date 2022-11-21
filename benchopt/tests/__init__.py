import sys
from pathlib import Path

from benchopt.benchmark import Benchmark

from benchopt.tests.utils.patch_benchmark import FakeModule


sys.modules['dummy_solver_import'] = FakeModule
sys.modules['dummy_dataset_import'] = FakeModule


# Default benchmark
TEST_BENCHMARK_DIR = Path(__file__).parent / 'test_benchmarks'
DUMMY_BENCHMARK_PATH = TEST_BENCHMARK_DIR / 'dummy_benchmark'
REQUIREMENT_BENCHMARK_PATH = TEST_BENCHMARK_DIR / 'requirement_benchmark'

# Pattern to select specific datasets or solvers.
SELECT_ONE_SIMULATED = r'simulated[n_features=200,rho=0]'
SELECT_ONE_PGD = r'python-pgd[step_size=1]'
SELECT_ONE_OBJECTIVE = r'dummy*[reg=0.1]'

try:
    DUMMY_BENCHMARK = Benchmark(DUMMY_BENCHMARK_PATH)
except Exception:
    DUMMY_BENCHMARK = None
try:
    TEST_OBJECTIVE = DUMMY_BENCHMARK.get_benchmark_objective()
    TEST_SOLVER = [s for s in DUMMY_BENCHMARK.get_solvers()
                   if s.name == "Solver-Test"][0]
    TEST_DATASET = [d for d in DUMMY_BENCHMARK.get_datasets()
                    if d.name == "Test-Dataset"][0]
except Exception:
    TEST_OBJECTIVE = None
    TEST_SOLVER = None
    TEST_DATASET = None
