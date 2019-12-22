import pytest


from benchopt.cli import run


def test_invalid_benchmark():
    with pytest.raises(AssertionError, match=r"{'fake_test'} is not"):
        run(['fake_test'], [], '')
