"""Helper to generate simulated data in benchopt."""
import numpy as np
from sklearn.utils import check_random_state


def make_correlated_data(n_samples=100, n_features=50, rho=0.6,
                         random_state=None):
    r"""Generate correlated design matrix with decaying correlation rho**|i-j|.

    The data are generated using an AR model with reason corr and innovation
    $\sigma^2 = 1 - \rho^2$,
    $$
        x_{i+1} = \rho x_i + \epsilon \quad
        where \quad \epsilon \sim \mathcal N(0, \sigma^2)
    $$
    The generated features have mean 0, variance 1 and the expected correlation
    structure
    $$
        \mathbb E[x_i] = 0~, \quad \mathbb E[x_i^2] = 1  \quad
        and \quad \mathbb E[x_ix_j] = \rho^{|i-j|}
    $$

    Parameters
    ----------
    n_samples: int
        Number of samples in the design matrix.
    n_features: int
        Number of features in the design matrix.
    corr: float
        Correlation $\rho$ between successive features. The element $C_{i, j}$
        in the correlation matrix will be $\rho^{|i-j|}$. This parameter
        should be selected in $[0, 1[$.
    random_state : int | RandomState instance | None (default)
        Determines random number generation for data generation. Use an int to
        make the randomness deterministic.

    Returns
    -------
    X: ndarray, shape (n_samples, n_features)
        A design matrix with Toeplitz covariance.
    """
    if not 0 <= rho < 1:
        raise ValueError("The correlation `rho` should be chosen in [0, 1[.")
    rng = check_random_state(random_state)

    sigma = np.sqrt(1 - rho * rho)
    U = rng.randn(n_samples)

    X = np.empty([n_samples, n_features])
    X[:, 0] = U
    for i in range(1, n_features):
        U *= rho
        U += sigma * rng.randn(n_samples)
        X[:, i] = U
    return X
