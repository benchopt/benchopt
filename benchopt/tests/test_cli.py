import re
from pathlib import Path

import click
import pytest

from benchopt.viz import PLOT_KINDS
from benchopt.cli import run, plot, check_install
from benchopt.utils.stream_redirection import SuppressStd


def test_invalid_benchmark():
    with pytest.raises(click.BadParameter, match=r"invalid_benchmark"):
        run(['invalid_benchmark'], 'benchopt', standalone_mode=False)


def test_invalid_dataset():
    with pytest.raises(click.BadParameter, match=r"invalid_dataset"):
        run(['benchmarks/lasso', '-l', '-d', 'invalid_dataset', '-s',
             'pgd'], 'benchopt', standalone_mode=False)


def test_invalid_solver():
    with pytest.raises(click.BadParameter, match=r"invalid_solver"):
        run(['benchmarks/lasso', '-l', '-s', 'invalid_solver'],
            'benchopt', standalone_mode=False)


def test_check_install():
    pgd_solver = Path(__file__).parent / '..' / '..' / 'benchmarks'
    pgd_solver = pgd_solver / 'lasso' / 'solvers' / 'python_pgd.py'
    with pytest.raises(SystemExit, match=r'0'):
        check_install([str(pgd_solver.resolve()), 'Solver'], 'benchopt')


def test_benchopt_run():
    out = SuppressStd()
    with out:
        run(['benchmarks/lasso', '-l', '-d', 'simulated*500', '-s',
             'pgd*False', '-n', '1', '-r', '1', '-p', '0.1', '--no-plot'],
            'benchopt', standalone_mode=False)

    output = out.output
    matches = re.findall('Simulated', output)
    assert len(matches) == 1, output
    matches = re.findall('Lasso', output)
    assert len(matches) == 1, output
    assert 'Python-PGD[use_acceleration=False]' in output
    assert 'Python-PGD[use_acceleration=True]' not in output


class TestPlotCmd:

    @classmethod
    def setup_class(cls):
        "Make sure at least one result file is available"

        out = SuppressStd()
        with out:
            run(['benchmarks/lasso', '-l', '-d', 'simulated*500', '-s',
                'pgd*False', '-n', '1', '-r', '1', '-p', '0.1', '--no-plot'],
                'benchopt', standalone_mode=False)
        result_file = re.findall(r'Saving result in: (.*\.csv)', out.output)[0]
        cls.result_file = result_file

    @classmethod
    def teardown_class(cls):
        "Make sure at least one result file is available"
        Path(cls.result_file).unlink()

    def test_plot_invalid_file(self):

        with pytest.raises(FileNotFoundError, match=r"invalid_file"):
            plot(['benchmarks/lasso', '-f', 'invalid_file'],
                 'benchopt', standalone_mode=False)

    def test_plot_invalid_kind(self):

        with pytest.raises(ValueError, match=r"invalid_kind"):

            plot(['benchmarks/lasso', '-k', 'invalid_kind'],
                 'benchopt', standalone_mode=False)

    @pytest.mark.parametrize('kind', PLOT_KINDS)
    def test_valid_call(self, kind):

        out = SuppressStd()
        with out:
            plot(['benchmarks/lasso', '-f', self.result_file, '-k', kind,
                  '--no-display'],
                 'benchopt', standalone_mode=False)
        saved_files = re.findall(r'Save .* as: (.*\.pdf)', out.output)
        assert len(saved_files) == 1
        saved_file = saved_files[0]
        assert kind in saved_file

        Path(saved_file).unlink()
