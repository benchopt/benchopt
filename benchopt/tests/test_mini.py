"""End-to-end tests for the benchopt.mini decorator-based API."""

import pytest
import numpy as np

from benchopt.mini import (
    dataset,
    solver,
    objective,
    get_benchmark,
    _MINI_OBJECTIVES,
    MiniBenchmark,
)
from benchopt.runner import run_benchmark


# ---------------------------------------------------------------------------
# Inline mini-benchmark (defined at module level so that the calling-file
# filter in get_benchmark() works correctly via _module_filename).
# ---------------------------------------------------------------------------

@dataset(size=50, random_state=42)
def simulated(size, random_state):
    rng = np.random.default_rng(random_state)
    X = rng.standard_normal(size)
    return dict(X=X)


@solver(name="GD mini", lr=[1e-1, 1e-2])
def gd_solver(n_iter, X, lr):
    beta = np.zeros_like(X)
    for _ in range(n_iter):
        beta -= lr * beta
    return dict(beta=beta)


@objective(name="Test Mini Benchmark")
def evaluate(beta):
    return dict(value=float(0.5 * beta.dot(beta)))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_get_benchmark_returns_mini_benchmark():
    bench = get_benchmark()
    assert isinstance(bench, MiniBenchmark)


def test_benchmark_has_correct_classes():
    bench = get_benchmark()
    assert bench.get_benchmark_objective() is evaluate
    assert simulated in bench.get_datasets()
    assert gd_solver in bench.get_solvers()


def test_benchmark_objective_name():
    bench = get_benchmark()
    assert bench.get_benchmark_objective().name == "Test Mini Benchmark"


def test_benchmark_solvers_have_run_once_strategy():
    bench = get_benchmark()
    for solver_cls in bench.get_solvers():
        assert solver_cls.sampling_strategy == "run_once"


def test_dataset_get_data():
    instance = simulated.get_instance(size=10, random_state=0)
    data = instance.get_data()
    assert "X" in data
    assert len(data["X"]) == 10


def test_objective_evaluate_result():
    instance = evaluate.get_instance()
    result = instance.evaluate_result(beta=np.array([3.0, 4.0]))
    assert "value" in result
    assert result["value"] == pytest.approx(12.5)


def test_objective_get_one_result():
    instance = evaluate.get_instance()
    one_result = instance.get_one_result()
    assert "beta" in one_result


def test_solver_set_objective_and_run():
    instance = gd_solver.get_instance(lr=1e-1)
    instance.set_objective(X=np.ones(5))
    instance.run(3)
    result = instance.get_result()
    assert "beta" in result


def test_run_benchmark_end_to_end():
    """Full run using run_benchmark with a MiniBenchmark instance."""
    bench = get_benchmark()
    output_file = run_benchmark(
        bench,
        max_runs=2,
        n_repetitions=1,
        plot_result=False,
        show_progress=False,
    )
    assert output_file is not None
    assert output_file.exists()

    import pandas as pd
    df = pd.read_parquet(output_file)
    assert not df.empty
    assert "objective_value" in df.columns
    # Should have one row per solver configuration
    assert len(df) >= 1


def test_run_benchmark_multiple_solver_params():
    """Check that parameter sweep produces multiple result rows."""
    bench = get_benchmark()
    output_file = run_benchmark(
        bench,
        max_runs=1,
        n_repetitions=1,
        plot_result=False,
        show_progress=False,
    )
    import pandas as pd
    df = pd.read_parquet(output_file)
    # gd_solver has lr=[1e-1, 1e-2] => 2 configurations
    solver_names = df["solver_name"].unique()
    assert len(solver_names) == 2


def test_get_benchmark_raises_without_objective():
    """get_benchmark() must raise if no @objective has been registered
    for the calling file (we simulate this by temporarily clearing the list).
    """
    original = list(_MINI_OBJECTIVES)
    _MINI_OBJECTIVES.clear()
    try:
        with pytest.raises(ValueError, match="@objective"):
            get_benchmark()
    finally:
        _MINI_OBJECTIVES.extend(original)
