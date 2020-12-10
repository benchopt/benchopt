import pytest
import numpy as np
from numpy.linalg import norm

from benchopt.datasets.simulated import make_correlated_data


def test_correlated():
    n_features = 52
    n_samples = 101
    X, y, w_true = make_correlated_data(
        n_samples=n_samples, n_features=n_features, random_state=42
    )
    assert X.shape == (n_samples, n_features)
    assert y.shape == (n_samples, )
    assert w_true.shape == (n_features, )


@pytest.mark.parametrize('snr', [0, 5, np.inf])
def test_correlated_snr(snr):
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


@pytest.mark.parametrize('param_name, p_range', [
    ('rho', [0, 1]), ('density', [0, 1]), ('snr', [0, np.inf])
])
def test_correlated_validation_check(param_name, p_range):
    min_val, max_val = p_range

    pattern = f'{param_name}.* should be chosen in .*{min_val}, {max_val}'
    if min_val == 0:
        with pytest.raises(ValueError, match=pattern):
            kwargs = {param_name: -1}
            make_correlated_data(**kwargs)

    if max_val == 1:
        with pytest.raises(ValueError, match=pattern):
            kwargs = {param_name: 2}
            make_correlated_data(**kwargs)
