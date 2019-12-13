from glob import glob

from benchopt import run_benchmark

benchs = glob("benchmarks/*/bench_*.py")
for b in benchs:
    b = b.replace('/', '.').replace('.py', '')
    run_benchmark(b)
