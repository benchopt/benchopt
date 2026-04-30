from benchopt import BaseDataset
import numpy as np


class Dataset(BaseDataset):
    """Simulated noisy 2D signal (small image-like array).

    Generates a clean 2D signal (checkerboard pattern) and
    adds Gaussian noise.
    """
    name = "simulated"

    parameters = {
        "n": [32],
        "noise_std": [0.3],
        "random_state": [42],
    }

    def get_data(self):
        rng = np.random.default_rng(self.random_state)
        # Checkerboard pattern as "true image"
        coords = np.arange(self.n)
        X_true = (
            (coords[:, None] // 4 + coords[None, :] // 4) % 2
        ).astype(float)
        X_noisy = X_true + rng.normal(0, self.noise_std, X_true.shape)
        return dict(X_true=X_true, X_noisy=X_noisy)
