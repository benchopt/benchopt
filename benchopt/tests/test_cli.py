import re
from pathlib import Path

import click
import pytest

from benchopt.cli import run, check_install
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
    assert 'Pgd[use_acceleration=false]' in output
    assert 'Pgd[use_acceleration=true]' not in output
