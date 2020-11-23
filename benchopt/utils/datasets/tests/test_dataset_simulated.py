import pytest
import numpy as np
from numpy.linalg import norm

from benchopt.utils.datasets.simulated import make_correlated_data


@pytest.mark.parametrize('snr', [0, 5, np.inf])
def test_correlated_given_coef(snr):
    n_features = 50
    X, y, w_true = make_correlated_data(
        n_samples=10000, n_features=n_features, snr=snr, random_state=42
    )
    y_pred = X @ w_true
    if snr == 0:
        assert abs(np.corrcoef(y_pred, y)[0, 1]) < 1e-2
    elif snr == np.inf:
        np.testing.assert_allclose(y, y_pred)
    else:
        np.testing.assert_allclose(
            snr, norm(y_pred) / norm(y - y_pred)
        )


@pytest.mark.parametrize('density', [.1, .5])
def test_correlated_w_true(density):
    n_features = 50
    X, y, w_true = make_correlated_data(
        n_features=n_features, density=density, random_state=42
    )

    assert len(w_true.nonzero()[0]) == int(density * n_features)

    X, y, w_new = make_correlated_data(
        n_features=n_features, density=density, w_true=w_true
    )

    assert all(w_new == w_true)
