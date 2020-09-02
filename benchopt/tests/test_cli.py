import click
import pytest
from pathlib import Path


from benchopt.cli import run, check_install


def test_invalid_benchmark():
    with pytest.raises(click.BadParameter, match=r"invalid_benchmark"):
        run(['invalid_benchmark'], 'benchopt', standalone_mode=False)


def test_invalid_dataset():
    with pytest.raises(click.BadParameter, match=r"invalid_dataset"):
        run(['benchmarks/lasso', '-l', '-d', 'invalid_dataset', '-s',
             'baseline'], 'benchopt', standalone_mode=False)


def test_invalid_solver():
    with pytest.raises(click.BadParameter, match=r"invalid_solver"):
        run(['benchmarks/lasso', '-l', '-s', 'invalid_solver'],
            'benchopt', standalone_mode=False)


def test_check_install():
    baseline = Path(__file__).parent / '..' / '..' / 'benchmarks'
    baseline = baseline / 'lasso' / 'solvers' / 'baseline.py'
    with pytest.raises(SystemExit, match=r'0'):
        check_install([str(baseline.resolve()), 'Solver'], 'benchopt')
