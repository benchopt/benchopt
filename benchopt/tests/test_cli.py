import pytest


from benchopt.cli import run


def test_invalid_benchmark():
    with pytest.raises(AssertionError, match=r"{'test'} is not"):
        run(['test'], ['bla'], '1')
