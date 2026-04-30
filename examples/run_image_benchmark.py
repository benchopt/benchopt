"""Image plot type for benchopt
==============================

This example demonstrates the ``image`` plot type, which allows
benchmark authors to display solver outputs as a visual gallery inside
the benchopt HTML result page.

The benchmark solves a toy 2-D signal denoising problem. Each solver
stores its intermediate iterates, and the custom ``reconstruction``
plot class encodes the final reconstruction of every solver as a
base64 PNG embedded directly in the HTML page.
"""

from benchopt.helpers.run_examples import ExampleBenchmark
from benchopt.helpers.run_examples import benchopt_cli

# %%
# Benchmark components
# --------------------
#
# We define each component (objective, dataset, solvers, custom plot) as an
# inline string and pass them to :class:`ExampleBenchmark`.  This mirrors the
# pattern used elsewhere in the examples folder.

OBJECTIVE = """
    from benchopt import BaseObjective
    import numpy as np

    class Objective(BaseObjective):
        name = "Image Denoising"

        def set_data(self, X_true, X_noisy):
            self.X_true = X_true
            self.X_noisy = X_noisy

        def get_objective(self):
            return dict(X_noisy=self.X_noisy)

        def evaluate_result(self, X_hat):
            return dict(value=float(np.mean((self.X_true - X_hat) ** 2)))

        def get_one_result(self):
            return dict(X_hat=self.X_noisy)
"""

DATASET = """
    from benchopt import BaseDataset
    import numpy as np

    class Dataset(BaseDataset):
        name = "simulated"
        parameters = {"n": [32], "noise_std": [0.3], "random_state": [42]}

        def get_data(self):
            rng = np.random.default_rng(self.random_state)
            coords = np.arange(self.n)
            X_true = (
                (coords[:, None] // 4 + coords[None, :] // 4) % 2
            ).astype(float)
            X_noisy = X_true + rng.normal(0, self.noise_std, X_true.shape)
            return dict(X_true=X_true, X_noisy=X_noisy)
"""

SOLVER_GAUSSIAN = """
    from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = "gaussian_filter"
        sampling_strategy = "callback"
        parameters = {"sigma": [0.5, 1.5]}

        def set_objective(self, X_noisy):
            self.X_noisy = X_noisy

        def run(self, cb):
            from scipy.ndimage import gaussian_filter
            self.X_hat = self.X_noisy.copy()
            while cb():
                self.X_hat = gaussian_filter(self.X_hat, sigma=self.sigma)

        def get_result(self):
            return dict(X_hat=self.X_hat)
"""

SOLVER_TV = """
    from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = "tv_denoise"
        sampling_strategy = "callback"
        parameters = {"lam": [0.05, 0.15]}

        def set_objective(self, X_noisy):
            self.X_noisy = X_noisy

        def run(self, cb):
            # Proximal gradient step for isotropic TV denoising
            # min_X 0.5*||X - X_noisy||^2 + lam*TV(X)
            # via forward-backward on the dual (Chambolle 2004)
            n = self.X_noisy.shape[0]
            # dual variables
            p = np.zeros((n, n, 2))
            self.X_hat = self.X_noisy.copy()
            self.iterates = [self.X_hat.copy()]
            tau = 0.24  # step size < 1/(2*lam) for stability
            while cb():
                # gradient of X w.r.t. dual
                div_p = np.zeros_like(self.X_hat)
                div_p[:-1, :] += p[:-1, :, 0]
                div_p[1:, :]  -= p[:-1, :, 0]
                div_p[:, :-1] += p[:, :-1, 1]
                div_p[:, 1:]  -= p[:, :-1, 1]
                X_upd = self.X_noisy + self.lam * div_p
                # gradient of X_upd
                grad = np.zeros((n, n, 2))
                grad[:-1, :, 0] = X_upd[1:, :] - X_upd[:-1, :]
                grad[:, :-1, 1] = X_upd[:, 1:] - X_upd[:, :-1]
                # dual step + projection
                p_new = p - tau * grad
                norms = np.maximum(
                    1.0,
                    np.sqrt((p_new ** 2).sum(axis=2, keepdims=True))
                )
                p = p_new / norms
                # primal update
                div_p = np.zeros_like(self.X_hat)
                div_p[:-1, :] += p[:-1, :, 0]
                div_p[1:, :]  -= p[:-1, :, 0]
                div_p[:, :-1] += p[:, :-1, 1]
                div_p[:, 1:]  -= p[:, :-1, 1]
                self.X_hat = self.X_noisy + self.lam * div_p

        def get_result(self):
            return dict(X_hat=self.X_hat)
"""

# %%
# The ``image`` plot type
# -----------------------
#
# A custom :class:`~benchopt.BasePlot` subclass with ``type = "image"`` must
# return from ``plot()`` a list of dicts, each with at least:
#
# - ``"src"`` — a base64 ``data:image/png;base64,...`` URI (or any URL);
# - ``"label"`` — displayed below the image card.
#
# ``get_metadata()`` may return ``"ncols"`` to control the grid layout.
#
# The plot reconstructs the dataset deterministically (same fixed seed) and
# re-applies each solver's algorithm using the parameters extracted from the
# solver name. This is the standard pattern: image plots generate visuals from
# the scalar benchmark results, not from serialised arrays.

PLOT = """
    import base64
    import io
    import re

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy.ndimage import gaussian_filter

    from benchopt import BasePlot


    def _make_dataset(n=32, noise_std=0.3, seed=42):
        # Reproduce the simulated dataset deterministically.
        rng = np.random.default_rng(seed)
        coords = np.arange(n)
        X_true = (
            (coords[:, None] // 4 + coords[None, :] // 4) % 2
        ).astype(float)
        return X_true, X_true + rng.normal(0, noise_std, X_true.shape)


    def _apply_solver(solver_name, X_noisy, n_steps=20):
        # Re-run the solver for n_steps and return the denoised image.
        X = X_noisy.copy()
        sigma_m = re.search(r"sigma=([0-9.]+)", solver_name)
        lam_m = re.search(r"lam=([0-9.]+)", solver_name)
        if sigma_m:
            sigma = float(sigma_m.group(1))
            for _ in range(n_steps):
                X = gaussian_filter(X, sigma=sigma)
        elif lam_m:
            lam = float(lam_m.group(1))
            n = X.shape[0]
            p = np.zeros((n, n, 2))
            tau = 0.24
            for _ in range(n_steps):
                div_p = np.zeros_like(X)
                div_p[:-1] += p[:-1, :, 0]; div_p[1:] -= p[:-1, :, 0]
                div_p[:, :-1] += p[:, :-1, 1]; div_p[:, 1:] -= p[:, :-1, 1]
                X_upd = X_noisy + lam * div_p
                grad = np.zeros((n, n, 2))
                grad[:-1, :, 0] = X_upd[1:] - X_upd[:-1]
                grad[:, :-1, 1] = X_upd[:, 1:] - X_upd[:, :-1]
                p_new = p - tau * grad
                p = p_new / np.maximum(1.0, np.sqrt(
                    (p_new ** 2).sum(axis=2, keepdims=True)
                ))
                div_p = np.zeros_like(X)
                div_p[:-1] += p[:-1, :, 0]; div_p[1:] -= p[:-1, :, 0]
                div_p[:, :-1] += p[:, :-1, 1]; div_p[:, 1:] -= p[:, :-1, 1]
                X = X_noisy + lam * div_p
        return X


    def _to_png(arr):
        fig, ax = plt.subplots(figsize=(3, 3))
        ax.imshow(np.clip(arr, 0, 1), cmap="gray", interpolation="nearest")
        ax.axis("off")
        fig.tight_layout(pad=0)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=80, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return "data:image/png;base64," + base64.b64encode(
            buf.read()
        ).decode("ascii")


    class Plot(BasePlot):
        name = "reconstruction"
        type = "image"
        options = {"dataset": ..., "objective": ...}

        def plot(self, df, dataset, objective):
            df = df.query(
                "dataset_name == @dataset and objective_name == @objective"
            )
            X_true, X_noisy = _make_dataset()
            # Add the noisy input as a reference card
            images = [{"src": _to_png(X_noisy), "label": "noisy input",
                        "caption": f"MSE={np.mean((X_true-X_noisy)**2):.4f}"}]
            for solver_name, sdf in df.groupby("solver_name"):
                mse = sdf[sdf["stop_val"] == sdf["stop_val"].max()][
                    "objective_value"
                ].iloc[0]
                X_hat = _apply_solver(solver_name, X_noisy)
                images.append({
                    "src": _to_png(X_hat),
                    "label": solver_name,
                    "caption": f"MSE={mse:.4f}",
                })
            return images

        def get_metadata(self, df, dataset, objective):
            n = len(df.query(
                "dataset_name == @dataset and objective_name == @objective"
            )["solver_name"].unique())
            return {
                "title": f"{objective} — Data: {dataset}",
                "ncols": min(n + 1, 4),  # +1 for the noisy reference
            }
"""

# %%
# Instantiate and display the benchmark
# -------------------------------------

benchmark = ExampleBenchmark(
    name="image_denoising",
    objective=OBJECTIVE,
    datasets={"simulated.py": DATASET},
    solvers={
        "gaussian_filter.py": SOLVER_GAUSSIAN,
        "tv_denoise.py": SOLVER_TV,
    },
    plots={"reconstruction.py": PLOT},
)
benchmark

# %%
# Run the benchmark
# -----------------
#
# We use a small ``-n`` and ``-r`` to keep the runtime short.

benchopt_cli(
    f"run {benchmark.benchmark_dir} -n 5 -r 1"
)

# %%
# In the resulting HTML page, select **reconstruction** in the *Chart type*
# dropdown to see the image grid. Each card shows the final denoised image
# produced by that solver configuration, with its MSE and number of steps.
#
# The image data is embedded as base64-encoded PNGs directly in the HTML
# file, so the page is fully self-contained.
