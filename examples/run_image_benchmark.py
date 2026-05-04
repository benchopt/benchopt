"""Image plot type for benchopt
==============================

This example demonstrates the ``image`` plot type, which allows
benchmark authors to display solver outputs as a visual gallery inside
the benchopt HTML result page.

The benchmark solves a toy 2-D signal denoising problem.
``evaluate_result`` returns per-iteration frames (``frame=X_hat``) and
``save_final_results`` stores the reference and noisy images once per run.
The custom ``reconstruction`` plot class reads those arrays directly from the
result DataFrame and renders an image grid with per-solver animated GIFs
and captions showing the solver name and MSE.
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
            return dict(
                value=float(np.mean((self.X_true - X_hat) ** 2)),
                frame=X_hat,
            )

        def save_final_results(self, X_hat):
            return dict(reference=self.X_true, noisy=self.X_noisy)

        def get_one_result(self):
            return dict(X_hat=self.X_noisy)
"""

DATASET = """
    from benchopt import BaseDataset
    import numpy as np

    class Dataset(BaseDataset):
        name = "simulated"
        parameters = {"n": [32, 128], "noise_std": [0.3], "random_state": [42]}

        def get_data(self):
            rng = np.random.default_rng(self.random_state)
            coords = np.arange(self.n)
            X_true = (
                (coords[:, None] // 4 + coords[None, :] // 4) % 2
            ).astype(float)
            X_noisy = X_true + rng.normal(0, self.noise_std, X_true.shape)
            return dict(X_true=X_true, X_noisy=X_noisy)
"""

SOLVER_MEDIAN = """
    from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = "median_filter"
        sampling_strategy = "callback"
        parameters = {"size": [3, 5]}

        def set_objective(self, X_noisy):
            self.X_noisy = X_noisy

        def run(self, cb):
            from scipy.ndimage import median_filter
            self.X_hat = self.X_noisy.copy()
            while cb():
                self.X_hat = median_filter(self.X_hat, size=self.size)

        def get_result(self):
            return dict(X_hat=self.X_hat)
"""

SOLVER_TV = """
    from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = "tv_denoise"
        sampling_strategy = "callback"
        parameters = {"lam": [0.1, 0.5]}

        def set_objective(self, X_noisy):
            self.X_noisy = X_noisy

        def run(self, cb):
            n = self.X_noisy.shape[0]
            p = np.zeros((n, n, 2))
            self.X_hat = self.X_noisy.copy()
            tau = 0.24
            while cb():
                div_p = np.zeros_like(self.X_hat)
                div_p[:-1, :] += p[:-1, :, 0]
                div_p[1:, :]  -= p[:-1, :, 0]
                div_p[:, :-1] += p[:, :-1, 1]
                div_p[:, 1:]  -= p[:, :-1, 1]
                X_upd = self.X_noisy + self.lam * div_p
                grad = np.zeros((n, n, 2))
                grad[:-1, :, 0] = X_upd[1:, :] - X_upd[:-1, :]
                grad[:, :-1, 1] = X_upd[:, 1:] - X_upd[:, :-1]
                p_new = p - tau * grad
                norms = np.maximum(
                    1.0,
                    np.sqrt((p_new ** 2).sum(axis=2, keepdims=True))
                )
                p = p_new / norms
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
# - ``"image"`` — a 2-D NumPy array (PNG) or a list of arrays (animated GIF);
# - ``"label"`` — text displayed below the image card.
#
# ``get_metadata()`` may return ``"ncols"`` to control the grid layout.
#
# ``evaluate_result`` returns ``frame=X_hat`` alongside the scalar ``value``.
# Non-primitive values are serialized inline into the parquet result file and
# restored automatically on read, so they appear as normal DataFrame columns.
# The plot collects all per-iteration frames from the ``objective_frame``
# column and passes the list to the ``"image"`` key; the framework converts
# a list of arrays to an animated GIF automatically.
# ``save_final_results`` stores the reference and noisy images once; the plot
# reads them from the ``final_results`` column.

PLOT = """
    import numpy as np
    from benchopt import BasePlot

    class Plot(BasePlot):
        name = "reconstruction"
        type = "image"
        options = {"dataset": ..., "objective": ...}

        def plot(self, df, dataset, objective):
            df = df.query(
                "dataset_name == @dataset and objective_name == @objective"
            )
            # Get reference and noisy from final_results (only stored once)
            final = df["final_results"].dropna().iloc[0]
            ref = final["reference"]
            noisy = final["noisy"]
            mse_noisy = float(np.mean((ref - noisy) ** 2))
            images = [
                {"image": ref, "label": "Reference"},
                {"image": noisy,
                 "label": f"Noisy input\\nMSE={mse_noisy:.4f}"},
            ]
            for solver_name, sdf in df.groupby("solver_name"):
                frames = (
                    sdf.sort_values("stop_val")["objective_frame"].tolist()
                )
                last_mse = sdf.loc[sdf["stop_val"].idxmax(), "objective_value"]
                images.append({
                    "image": frames,  # list of arrays → animated GIF
                    "label": f"{solver_name}\\nMSE={last_mse:.4f}",
                })
            return images

        def get_metadata(self, df, dataset, objective):
            n = len(df.query(
                "dataset_name == @dataset and objective_name == @objective"
            )["solver_name"].unique())
            return {
                "title": f"{objective} — Data: {dataset}",
                "ncols": min(n + 2, 4),  # +2 for reference and noisy input
            }
"""

CONFIG = """
plots:
- reconstruction
- objective_curve
- bar_chart
- boxplot
- table
"""

# %%
# Instantiate and display the benchmark
# -------------------------------------

benchmark = ExampleBenchmark(
    name="image_denoising",
    objective=OBJECTIVE,
    datasets={"simulated.py": DATASET},
    solvers={
        "tv_denoise.py": SOLVER_TV,
        "median_filter.py": SOLVER_MEDIAN,
    },
    plots={"reconstruction.py": PLOT},
    extra_files={"config.yml": CONFIG},
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
# dropdown to see the image grid. Each card shows an animated GIF of the
# solver iterating toward its final denoised image, alongside its MSE.
# Reference and noisy images are shown for comparison.
# All arrays are embedded as base64-encoded data URIs directly in the HTML
# file, so the page is fully self-contained.
