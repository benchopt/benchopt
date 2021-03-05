import re
from pathlib import Path

import click
import pytest

from benchopt.plotting import PLOT_KINDS
from benchopt.utils.stream_redirection import SuppressStd


from benchopt.tests import SELECT_ONE_PGD
from benchopt.tests import SELECT_ONE_SIMULATED
from benchopt.tests import DUMMY_BENCHMARK_PATH


from benchopt.cli.main import run
from benchopt.cli.process_results import plot
from benchopt.cli.helpers import check_install


class TestCheckInstallCmd:
    def test_solver_installed(self):
        pgd_solver = DUMMY_BENCHMARK_PATH / 'solvers' / 'python_pgd.py'
        with pytest.raises(SystemExit, match=r'0'):
            check_install([str(pgd_solver.resolve()), 'Solver'], 'benchopt')

    def test_solver_does_not_exists(self):
        pgd_solver = DUMMY_BENCHMARK_PATH / 'solvers' / 'invalid.py'
        with pytest.raises(FileNotFoundError, match=r'invalid.py'):
            check_install([str(pgd_solver.resolve()), 'Solver'], 'benchopt')

    def test_dataset_installed(self):
        pgd_solver = DUMMY_BENCHMARK_PATH / 'datasets' / 'simulated.py'
        with pytest.raises(SystemExit, match=r'0'):
            check_install([str(pgd_solver.resolve()), 'Dataset'], 'benchopt')

    def test_dataset_does_not_exists(self):
        pgd_solver = DUMMY_BENCHMARK_PATH / 'datasets' / 'invalid.py'
        with pytest.raises(FileNotFoundError, match=r'invalid.py'):
            check_install([str(pgd_solver.resolve()), 'Dataset'], 'benchopt')


class CaptureRunOutput(object):
    """Context to capture run cmd output and files.
    """

    def __init__(self):
        self.out = SuppressStd()
        self.output = None
        self.result_files = []

    def __enter__(self):
        self.output = None
        self.result_files = []

        # Redirect the stdout/stderr fd to temp file
        self.out.__enter__()
        return self

    def __exit__(self, type, value, traceback):
        self.out.__exit__(type, value, traceback)
        self.output = self.out.output

        # Make sure to delete all the result that created by the run command.
        self.result_files = re.findall(
            r'Saving result in: (.*\.csv)', self.output
        )
        if len(self.result_files) >= 1:
            for result_file in self.result_files:
                Path(result_file).unlink()

        if type is not None:
            print(self.output)

    def check_output(self, pattern, repetition=None):
        matches = re.findall(pattern, self.output)
        if repetition is None:
            assert len(matches) > 0, self.output
        else:
            assert len(matches) == repetition, self.output


class TestRunCmd:

    @pytest.mark.parametrize('invalid_benchmark, match', [
        ('invalid_benchmark', "Path 'invalid_benchmark' does not exist."),
        ('.', "The folder '.' does not contain `objective.py`")],
        ids=['invalid_path', 'no_objective'])
    def test_invalid_benchmark(self, invalid_benchmark, match):
        with pytest.raises(click.BadParameter, match=match):
            run([invalid_benchmark], 'benchopt', standalone_mode=False)

    def test_invalid_dataset(self):
        with pytest.raises(click.BadParameter, match=r"invalid_dataset"):
            run([str(DUMMY_BENCHMARK_PATH), '-l', '-d', 'invalid_dataset',
                 '-s', 'pgd'], 'benchopt', standalone_mode=False)

    def test_invalid_solver(self):
        with pytest.raises(click.BadParameter, match=r"invalid_solver"):
            run([str(DUMMY_BENCHMARK_PATH), '-l', '-s', 'invalid_solver'],
                'benchopt', standalone_mode=False)

    def test_benchopt_run(self):
        with CaptureRunOutput() as out:
            run([str(DUMMY_BENCHMARK_PATH), '-l', '-d', SELECT_ONE_SIMULATED,
                 '-f', SELECT_ONE_PGD, '-n', '1', '-r', '1', '-p', '0.1',
                 '--no-plot'], 'benchopt', standalone_mode=False)

        out.check_output('Simulated', repetition=1)
        out.check_output('Dummy Sparse Regression', repetition=1)
        out.check_output(r'Python-PGD\[step_size=1\]', repetition=3)
        out.check_output(r'Python-PGD\[step_size=1.5\]', repetition=0)

        # Make sure the results were saved in a result file
        assert len(out.result_files) == 1, out.output

    def test_benchopt_run_in_env(self, test_env_name):
        with CaptureRunOutput() as out:
            with pytest.raises(SystemExit, match='False'):
                run([str(DUMMY_BENCHMARK_PATH), '--env-name', test_env_name,
                     '-d', SELECT_ONE_SIMULATED, '-f', SELECT_ONE_PGD,
                     '-n', '1', '-r', '1', '-p', '0.1', '--no-plot'],
                    'benchopt', standalone_mode=False)

        out.check_output(f'conda activate {test_env_name}')
        out.check_output('Simulated', repetition=1)
        out.check_output('Dummy Sparse Regression', repetition=1)
        out.check_output(r'Python-PGD\[step_size=1\]', repetition=3)
        out.check_output(r'Python-PGD\[step_size=1.5\]', repetition=0)

        # Make sure the results were saved in a result file
        assert len(out.result_files) == 1, out.output

    def test_benchopt_caching(self):

        n_rep = 2
        run_cmd = [str(DUMMY_BENCHMARK_PATH), '-l', '-d', SELECT_ONE_SIMULATED,
                   '-s', SELECT_ONE_PGD, '-n', '1', '-r', str(n_rep),
                   '-p', '0.1', '--no-plot']

        # Make a first run that should be put in cache
        with CaptureRunOutput() as out:
            run(run_cmd, 'benchopt', standalone_mode=False)

        # Now check that the cache is hit when running the benchmark a
        # second time without force
        with CaptureRunOutput() as out:
            run(run_cmd, 'benchopt', standalone_mode=False)

        out.check_output(r'Python-PGD\[step_size=1\]',
                         repetition=1)

        # Make sure that -f option forces the re-run for the solver
        run_cmd[4] = '-f'
        with CaptureRunOutput() as out:
            run(run_cmd, 'benchopt', standalone_mode=False)

        out.check_output(r'Python-PGD\[step_size=1\]',
                         repetition=2*n_rep+1)


class TestPlotCmd:

    @classmethod
    def setup_class(cls):
        "Make sure at least one result file is available"
        with SuppressStd() as out:
            run([str(DUMMY_BENCHMARK_PATH), '-l', '-d', SELECT_ONE_SIMULATED,
                 '-s', SELECT_ONE_PGD, '-n', '2', '-r', '1', '-p', '0.1',
                 '--no-plot'], 'benchopt', standalone_mode=False)
        result_files = re.findall(r'Saving result in: (.*\.csv)', out.output)
        assert len(result_files) == 1, out.output
        result_file = result_files[0]
        cls.result_file = result_file

    @classmethod
    def teardown_class(cls):
        "Make sure at least one result file is available"
        Path(cls.result_file).unlink()

    def test_plot_invalid_file(self):

        with pytest.raises(FileNotFoundError, match=r"invalid_file"):
            plot([str(DUMMY_BENCHMARK_PATH), '-f', 'invalid_file'],
                 'benchopt', standalone_mode=False)

    def test_plot_invalid_kind(self):

        with pytest.raises(ValueError, match=r"invalid_kind"):

            plot([str(DUMMY_BENCHMARK_PATH), '-k', 'invalid_kind'],
                 'benchopt', standalone_mode=False)

    @pytest.mark.parametrize('kind', PLOT_KINDS)
    def test_valid_call(self, kind):

        with SuppressStd() as out:
            plot([str(DUMMY_BENCHMARK_PATH), '-f', self.result_file,
                  '-k', kind, '--no-display'],
                 'benchopt', standalone_mode=False)
        saved_files = re.findall(r'Save .* as: (.*\.pdf)', out.output)
        assert len(saved_files) == 1
        saved_file = saved_files[0]
        assert kind in saved_file

        Path(saved_file).unlink()
