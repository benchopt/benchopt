import pytest
import numpy as np
from scipy import sparse
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


@pytest.mark.parametrize('n_tasks', [1, 7])
def test_correlated_n_tasks(n_tasks):
    X, y, w_true = make_correlated_data(
        n_tasks=n_tasks, random_state=42
    )

    if n_tasks == 1:
        assert y.ndim == 1
        assert w_true.ndim == 1
    else:
        assert y.ndim == 2
        assert y.shape[1] == w_true.shape[1]


@pytest.mark.parametrize("X_density", [-1, 0.2, 0.7, 1, 1.2])
def test_correlated_sparse_X(X_density):
    if not 0 < X_density <= 1:
        np.testing.assert_raises(ValueError, make_correlated_data,
                                 X_density=X_density)
    else:
        X, y, _ = make_correlated_data(X_density=X_density, random_state=0)
        if X_density == 1:
            assert isinstance(X, np.ndarray)
        else:
            assert isinstance(X, sparse.csc_matrix)
            # check that X's density is equal to X_density up to sampling noise
            np.testing.assert_allclose(
                X_density * X.shape[0] * X.shape[1], len(X.indices - 1),
                rtol=0.05)


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
