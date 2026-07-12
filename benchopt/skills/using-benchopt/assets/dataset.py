import numpy as np
from benchopt import BaseDataset


class Dataset(BaseDataset):
    name = "simulated"
    requirements = []
    parameters = {
        "n_samples": [100, 1000],
        "n_features": [20],
    }
    # Params that don't affect prepare() output (omit or set to "all"):
    # prepare_cache_ignore = ("seed",)

    def get_data(self):
        # Must return a dict; benchopt calls Objective.set_data(**data).
        # get_seed(use_repetition=True) makes --n-repetitions draw distinctly.
        rng = np.random.default_rng(self.get_seed(use_repetition=True))
        X = rng.standard_normal((self.n_samples, self.n_features))
        y = X @ rng.standard_normal(self.n_features)
        return dict(X=X, y=y)

    # Optional: expensive one-time work (downloads, preprocessing).
    # benchopt run never calls prepare(); trigger via `benchopt prepare .`
    # or share an _ensure_prepared() guard called from both.
    # def prepare(self):
    #     ...  # idempotent; safe to re-run


# Minimal zero-dependency smoke-test dataset — keeps `benchopt test` fast.
class SimulatedSmall(BaseDataset):
    name = "simulated-small"
    requirements = []
    parameters = {"n_samples": [50], "n_features": [10]}
    test_parameters = {"n_samples": [10], "n_features": [5]}

    def get_data(self):
        rng = np.random.default_rng(self.get_seed(use_repetition=True))
        X = rng.standard_normal((self.n_samples, self.n_features))
        y = X @ rng.standard_normal(self.n_features)
        return dict(X=X, y=y)
