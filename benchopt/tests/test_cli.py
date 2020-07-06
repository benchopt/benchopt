import pytest


from benchopt.cli import run


def test_invalid_benchmark():
    with pytest.raises(SystemExit, match=r"2"):
        run(['invalid_benchmark'], 'benchopt')


def test_invalid_dataset():
    with pytest.raises(AssertionError, match=r"invalid_dataset"):
        run(['lasso', '-l', '-d', 'invalid_dataset', '-s', 'baseline'],
            'benchopt')
