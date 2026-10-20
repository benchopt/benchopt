"""
Benchopt debugging snippet — run from the benchmark directory:
    python -i debug_snippet.py
or paste into a notebook.
"""
from benchopt.benchmark import Benchmark

bench = Benchmark(".")

# --- Inspect a dataset ---
datasets = bench.get_datasets()
Dataset = next(d for d in datasets if d.name == "simulated")
data = Dataset.get_instance(n_samples=100).get_data()
print("data keys:", list(data.keys()))

# --- Inspect the objective ---
Objective = bench.get_benchmark_objective()
objective = Objective.get_instance()
objective.set_data(**data)

obj_dict = objective.get_objective()
print("objective dict keys:", list(obj_dict.keys()))

# --- Drive a solver by hand ---
solvers = bench.get_solvers()
Solver = next(s for s in solvers if s.name == "my-solver")
solver = Solver.get_instance()

skip, reason = solver.skip(**obj_dict)
if skip:
    print(f"Solver skipped: {reason}")
else:
    solver.set_objective(**obj_dict)
    solver.run(10)              # adjust arg to match sampling_strategy
    result = solver.get_result()

    metrics = objective.evaluate_result(**result)
    print("metrics:", metrics)

# --- Validate evaluate_result on an arbitrary checkpoint ---
# import numpy as np
# metrics = objective.evaluate_result(beta=np.zeros(data["X"].shape[1]))
# print(metrics)
