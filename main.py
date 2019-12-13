from glob import glob
from importlib import import_module

benchs = glob("benchmarks/*/bench_*.py")
for b in benchs:
    b = b.replace('/', '.').replace('.py', '')
    module = import_module(b)
    module.benchmark()
