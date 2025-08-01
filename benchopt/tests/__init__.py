import sys
from pathlib import Path

from benchopt.benchmark import Benchmark

from benchopt.tests.utils.patch_benchmark import FakeModule


sys.modules['dummy_solver_import'] = FakeModule
sys.modules['dummy_dataset_import'] = FakeModule


# Default benchmark
DUMMY_BENCHMARK_PATH = Path(__file__).parent / 'dummy_benchmark'

try:
    DUMMY_BENCHMARK = Benchmark(DUMMY_BENCHMARK_PATH)
except Exception:
    DUMMY_BENCHMARK = None
try:
    TEST_DATASET = [d for d in DUMMY_BENCHMARK.get_datasets()
                    if d.name == "Test-Dataset"][0]
except Exception:
    TEST_DATASET = None
