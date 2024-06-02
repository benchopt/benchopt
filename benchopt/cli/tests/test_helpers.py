import pytest


from benchopt.tests import DUMMY_BENCHMARK_PATH
from benchopt.tests.utils import CaptureRunOutput
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.utils.terminal_output import TICK, CROSS


from benchopt.cli.helpers import check_data
from benchopt.cli.helpers import check_install


class TestCheckInstallCmd:
    def test_solver_installed(self):
        pgd_solver = DUMMY_BENCHMARK_PATH / 'solvers' / 'python_pgd.py'
        with pytest.raises(SystemExit, match=r'0'):
            check_install([
                str(DUMMY_BENCHMARK_PATH), str(pgd_solver.resolve()), 'Solver'
            ], 'benchopt')

    def test_solver_does_not_exists(self):
        pgd_solver = DUMMY_BENCHMARK_PATH / 'solvers' / 'invalid.py'
        with pytest.raises(FileNotFoundError, match=r'invalid.py'):
            check_install([
                str(DUMMY_BENCHMARK_PATH), str(pgd_solver.resolve()), 'Solver'
            ], 'benchopt')

    def test_dataset_installed(self):
        pgd_solver = DUMMY_BENCHMARK_PATH / 'datasets' / 'simulated.py'
        with pytest.raises(SystemExit, match=r'0'):
            check_install([
                str(DUMMY_BENCHMARK_PATH), str(pgd_solver.resolve()), 'Dataset'
            ], 'benchopt')

    def test_dataset_does_not_exists(self):
        pgd_solver = DUMMY_BENCHMARK_PATH / 'datasets' / 'invalid.py'
        with pytest.raises(FileNotFoundError, match=r'invalid.py'):
            check_install([
                str(DUMMY_BENCHMARK_PATH), str(pgd_solver.resolve()), 'Dataset'
            ], 'benchopt')


class TestCheckDataCmd:
    def test_download_data(self):

        # Make sure that when the Objective is not installed, due to a missing
        # dependency, an error is raised.
        dataset = """from benchopt import BaseDataset

        class Dataset(BaseDataset):
            name = 'test_data'
            def get_data(self):
                print("LOADING DATA")
                return {'X': 1, 'y': 2}
        """
        with temp_benchmark(datasets=dataset) as benchmark:
            with CaptureRunOutput() as out:
                check_data(
                    [str(benchmark.benchmark_dir), '-d', 'test_data'],
                    'benchopt', standalone_mode=False
                )

            out.check_output("LOADING DATA", repetition=1)
            out.check_output(TICK, repetition=1)

    def test_fail_download_data(self):

        # Make sure that when the Objective is not installed, due to a missing
        # dependency, an error is raised.
        dataset = """from benchopt import BaseDataset

        class Dataset(BaseDataset):
            name = 'test_data'
            def get_data(self):
                raise ValueError("Failed to load data")
                return {'X': 1, 'y': 2}
        """
        with temp_benchmark(datasets=dataset) as benchmark:
            with CaptureRunOutput() as out:
                check_data(
                    [str(benchmark.benchmark_dir), '-d', 'test_data'],
                    'benchopt', standalone_mode=False
                )

            out.check_output(CROSS, repetition=1)
            out.check_output("ValueError: Failed to load data", repetition=1)
