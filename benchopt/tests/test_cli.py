import pytest


from benchopt.cli import run


def test_invalid_benchmark():
    with pytest.raises(SystemExit, match=r"2"):
        run(['invalid_benchmark'], 'benchopt')


def test_invalid_dataset():
    with pytest.raises(SystemExit, match=r"2"):
        run(['lasso', '-d', 'invalid_dataset'], 'benchopt')
