"""Helper to generate simulated data in benchopt."""
import numpy as np
from numpy.linalg import norm

from ..utils.checkers import check_random_state


def make_correlated_data(n_samples=100, n_features=50, rho=0.6, snr=3,
                         w_true=None, density=0.2, random_state=None):

    r"""Generate a linear regression with decaying correlation for the design
    matrix :math:`\rho^{|i-j|}`.

    The data are generated according to:

    .. math ::
        y = X w^* + \epsilon

    such that the signal to noise ratio is
    :math:`snr = \frac{||X w^*||}{||\epsilon||}`.

    The generated features have mean 0, variance 1 and the expected correlation
    structure

    .. math ::
        \mathbb E[x_i] = 0~, \quad \mathbb E[x_i^2] = 1  \quad
        and \quad \mathbb E[x_ix_j] = \rho^{|i-j|}

    Parameters
    ----------
    n_samples: int
        Number of samples in the design matrix.
    n_features: int
        Number of features in the design matrix.
    rho: float
        Correlation :math:`\rho` between successive features. The cross
        correlation :math:`C_{i, j}` between feature i and feature j will be
        :math:`\rho^{|i-j|}`. This parameter should be selected in
        :math:`[0, 1[`.
    snr : float
        Signal-to-noise ratio.
    w_true: np.array, shape (n_features,) | None
        True regression coefficients. If None, a sparse array with standard
        Gaussian non zero entries is simulated.
    density: float
        Proportion of non zero elements in w_true if the latter is simulated.
    random_state : int | RandomState instance | None (default)
        Determines random number generation for data generation. Use an int to
        make the randomness deterministic.

    Returns
    -------
    X: ndarray, shape (n_samples, n_features)
        A design matrix with Toeplitz covariance.
    y: ndarray, shape (n_samples,)
        Observation vector.
    w_true: ndarray, shape (n_features,)
        True regression vector of the model.
    """
    if not 0 <= rho < 1:
        raise ValueError("The correlation `rho` should be chosen in [0, 1[.")
    if not 0 < density <= 1:
        raise ValueError("The density should be chosen in ]0, 1].")
    if snr < 0:
        raise ValueError("The snr should be chosen in [0, inf].")
    rng = check_random_state(random_state)
    nnz = int(density * n_features)

    if rho != 0:
        # X is generated cleverly using an AR model with reason corr and i
        # innovation sigma^2 = 1 - \rho ** 2: X[:, j+1] = rho X[:, j] + eps_j
        # where eps_j = sigma * rng.randn(n_samples)
        sigma = np.sqrt(1 - rho * rho)
        U = rng.randn(n_samples)

        X = np.empty([n_samples, n_features], order='F')
        X[:, 0] = U
        for j in range(1, n_features):
            U *= rho
            U += sigma * rng.randn(n_samples)
            X[:, j] = U
    else:
        X = rng.randn(n_samples, n_features)

    if w_true is None:
        w_true = np.zeros(n_features)
        support = rng.choice(n_features, nnz, replace=False)
        w_true[support] = rng.randn(nnz)

    y = X @ w_true
    noise = rng.randn(n_samples)
    if snr not in [0, np.inf]:
        y += noise / norm(noise) * norm(y) / snr
    elif snr == 0:
        y = noise

    return X, y, w_true
