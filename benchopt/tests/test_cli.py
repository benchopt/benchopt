import re
from pathlib import Path

import click
import pytest

from benchopt.viz import PLOT_KINDS
from benchopt.cli import run, plot, check_install
from benchopt.utils.stream_redirection import SuppressStd


from benchopt.tests import DUMMY_BENCHMARK


class TestCheckInstallCmd:
    def test_solver_installed(self):
        pgd_solver = DUMMY_BENCHMARK / 'solvers' / 'python_pgd.py'
        with pytest.raises(SystemExit, match=r'0'):
            check_install([str(pgd_solver.resolve()), 'Solver'], 'benchopt')

    def test_solver_does_not_exists(self):
        pgd_solver = DUMMY_BENCHMARK / 'solvers' / 'invalid.py'
        with pytest.raises(FileNotFoundError, match=r'invalid.py'):
            check_install([str(pgd_solver.resolve()), 'Solver'], 'benchopt')

    def test_dataset_installed(self):
        pgd_solver = DUMMY_BENCHMARK / 'datasets' / 'simulated.py'
        with pytest.raises(SystemExit, match=r'0'):
            check_install([str(pgd_solver.resolve()), 'Dataset'], 'benchopt')

    def test_dataset_does_not_exists(self):
        pgd_solver = DUMMY_BENCHMARK / 'datasets' / 'invalid.py'
        with pytest.raises(FileNotFoundError, match=r'invalid.py'):
            check_install([str(pgd_solver.resolve()), 'Dataset'], 'benchopt')


class TestRunCmd:

    def test_invalid_benchmark(self):
        with pytest.raises(click.BadParameter, match=r"invalid_benchmark"):
            run(['invalid_benchmark'], 'benchopt', standalone_mode=False)

    def test_invalid_dataset(self):
        with pytest.raises(click.BadParameter, match=r"invalid_dataset"):
            run([str(DUMMY_BENCHMARK), '-l', '-d', 'invalid_dataset', '-s',
                'pgd'], 'benchopt', standalone_mode=False)

    def test_invalid_solver(self):
        with pytest.raises(click.BadParameter, match=r"invalid_solver"):
            run([str(DUMMY_BENCHMARK), '-l', '-s', 'invalid_solver'],
                'benchopt', standalone_mode=False)

    def test_benchopt_run(self):
        out = SuppressStd()
        with out:
            run([str(DUMMY_BENCHMARK), '-l', '-d', 'simulated*500', '-s',
                'pgd*False', '-n', '1', '-r', '1', '-p', '0.1', '--no-plot'],
                'benchopt', standalone_mode=False)

        output = out.output
        matches = re.findall('Simulated', output)
        assert len(matches) == 1, output
        matches = re.findall('Lasso', output)
        assert len(matches) == 1, output
        matches = re.findall(r'Python-PGD\[use_acceleration=False\]', output)
        assert len(matches) == 2, output
        assert 'Python-PGD[use_acceleration=True]' not in output

        # Make sure the results were saved in a result file
        # and delete it to avoid polluting result directory
        result_files = re.findall(r'Saving result in: (.*\.csv)', out.output)
        assert len(result_files) == 1, out.output
        result_file = result_files[0]
        Path(result_file).unlink()


class TestPlotCmd:

    @classmethod
    def setup_class(cls):
        "Make sure at least one result file is available"

        out = SuppressStd()
        with out:
            run([str(DUMMY_BENCHMARK), '-l', '-d', 'simulated*500', '-s',
                'pgd*False', '-n', '1', '-r', '1', '-p', '0.1', '--no-plot'],
                'benchopt', standalone_mode=False)
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
            plot([str(DUMMY_BENCHMARK), '-f', 'invalid_file'],
                 'benchopt', standalone_mode=False)

    def test_plot_invalid_kind(self):

        with pytest.raises(ValueError, match=r"invalid_kind"):

            plot([str(DUMMY_BENCHMARK), '-k', 'invalid_kind'],
                 'benchopt', standalone_mode=False)

    @pytest.mark.parametrize('kind', PLOT_KINDS)
    def test_valid_call(self, kind):

        out = SuppressStd()
        with out:
            plot([str(DUMMY_BENCHMARK), '-f', self.result_file, '-k', kind,
                  '--no-display'],
                 'benchopt', standalone_mode=False)
        saved_files = re.findall(r'Save .* as: (.*\.pdf)', out.output)
        assert len(saved_files) == 1
        saved_file = saved_files[0]
        assert kind in saved_file

        Path(saved_file).unlink()
