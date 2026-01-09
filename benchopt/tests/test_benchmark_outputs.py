import pandas as pd

from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.runner import run_benchmark


def test_filename_in_parquet():
    solver_file = """from benchopt import BaseSolver
    class Solver(BaseSolver):
        name = "{name}"
        sampling_strategy = 'run_once'
        def set_objective(self, X, y, lmbd): pass
        def run(self, n_iter): pass
        def get_result(self): return dict(beta=1)
    """
    solvers = {
        'test_solver.py': solver_file.format(name='test-solver'),
        'another_solver.py': solver_file.format(name='another-solver'),
    }
    dataset_file = """from benchopt import BaseDataset
    class Dataset(BaseDataset):
        name = "{name}"
        def get_data(self): return dict(X=1, y=1)
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
        )

        assert output_file.exists()
        assert output_file.suffix == '.parquet'

        df = pd.read_parquet(output_file)
        file_objective = df['file_objective'].unique()
        assert set(file_objective) == {"objective.py"}

        solver_files = df['file_solver'].unique()
        assert set(solver_files) == {"solvers/test_solver.py",
                                     "solvers/another_solver.py"}

        dataset_files = df['file_dataset'].unique()
        assert set(dataset_files) == {"datasets/test_dataset.py",
                                      "datasets/simulated.py"}
