import warnings

import pandas as pd

from benchopt.runner import run_benchmark
from benchopt.results import read_results, save_results
from benchopt.utils.temp_benchmark import temp_benchmark


def test_filename_in_parquet():
    solver_file = """from benchopt.utils.temp_benchmark import TempSolver
    class Solver(TempSolver):
        name = "{name}"
    """
    solvers = {
        'test_solver.py': solver_file.format(name='test-solver'),
        'another_solver.py': solver_file.format(name='another-solver'),
    }
    dataset_file = """from benchopt.utils.temp_benchmark import TempDataset
    class Dataset(TempDataset):
        name = "{name}"
    """
    datasets = {
        'test_dataset.py': dataset_file.format(name='test-dataset'),
        'simulated.py': dataset_file.format(name='simulated'),
    }
    with temp_benchmark(solvers=solvers, datasets=datasets) as bench:
        print(list((bench.benchmark_dir / 'solvers').glob("*.py")))
        output_file = run_benchmark(
            str(bench.benchmark_dir),
            output_file='results.parquet',
            plot_result=False,
            max_runs=0,
        )

        assert output_file.exists()
        assert output_file.suffix == '.parquet'

        df = read_results(output_file)
        file_objective = df['file_objective'].unique()
        assert set(file_objective) == {"objective.py"}

        solver_files = df['file_solver'].unique()
        assert set(solver_files) == {"solvers/test_solver.py",
                                     "solvers/another_solver.py"}

        dataset_files = df['file_dataset'].unique()
        assert set(dataset_files) == {"datasets/test_dataset.py",
                                      "datasets/simulated.py"}


def test_save_results_suffix(tmp_path):
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    out_path = tmp_path / "results.xyz"

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        saved = save_results(df, out_path, uniquify=False)

    assert saved.suffix == ".parquet"
    assert saved.exists()
    assert any(
        "Unsupported file format" in str(w.message) for w in caught
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        saved = save_results(df, out_path.with_suffix(""), uniquify=False)

    assert saved.suffix == ".parquet"
    assert saved.exists()
    assert all(
        "Unsupported file format" not in str(w.message) for w in caught
    )
