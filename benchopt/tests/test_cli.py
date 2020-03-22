import pytest
import subprocess
import numpy as np

from benchopt.cli import run


def test_invalid_benchmark():
    with pytest.raises(SystemExit, match=r"2"):
        run(['invalid_benchmark'], 'benchopt')


def test_invalid_dataset():
    with pytest.raises(SystemExit, match=r"2"):
        run(['lasso', '-d', 'invalid_dataset', '-s', 'baseline'], 'benchopt')


def test_invalid_solver():
    np.testing.assert_raises(ValueError, subprocess.Popen,
                             'benchopt run lasso -s sdjglsdglxcnv'.split())
