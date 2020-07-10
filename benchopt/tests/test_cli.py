import click
import pytest


from benchopt.cli import run, check_install


def test_invalid_benchmark():
    with pytest.raises(click.BadParameter, match=r"invalid_benchmark"):
        run(['invalid_benchmark'], 'benchopt', standalone_mode=False)


def test_invalid_dataset():
    with pytest.raises(click.BadParameter, match=r"invalid_dataset"):
        run(['lasso', '-l', '-d', 'invalid_dataset', '-s', 'baseline'],
            'benchopt', standalone_mode=False)


def test_invalid_solver():
    with pytest.raises(click.BadParameter, match=r"invalid_solver"):
        run(['lasso', '-l', '-s', 'invalid_solver'],
            'benchopt', standalone_mode=False)


def test_check_install():
    with pytest.raises(SystemExit, match=r'0'):
        check_install(['lasso', 'baseline'], 'benchopt')
