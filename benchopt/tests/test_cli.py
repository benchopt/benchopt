import click
import pytest


from benchopt.cli import run


def test_invalid_benchmark():
    with pytest.raises(click.BadParameter, match=r"invalid_benchmark"):
        run(['invalid_benchmark'], 'benchopt', standalone_mode=False)


def test_invalid_dataset():
    with pytest.raises(click.BadParameter, match=r"invalid_dataset"):
        run(['lasso', '-l', '-d', 'invalid_dataset', '-s', 'baseline'],
            'benchopt', standalone_mode=False)
