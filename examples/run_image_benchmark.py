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

        def evaluate_result(self, X_hat, iterates=None):
            result = dict(value=float(np.mean((self.X_true - X_hat) ** 2)))
            if iterates is not None:
                result["iterates"] = iterates
            return result

        def get_one_result(self):
            return dict(X_hat=self.X_noisy, iterates=None)
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
        requirements = ["scikit-image"]
        sampling_strategy = "callback"
        parameters = {"sigma": [0.5, 1.5]}

        def set_objective(self, X_noisy):
            self.X_noisy = X_noisy
            self.iterates = []

        def run(self, cb):
            from skimage.filters import gaussian
            self.X_hat = self.X_noisy.copy()
            self.iterates = [self.X_hat.copy()]
            while cb(self):
                self.X_hat = gaussian(self.X_hat, sigma=self.sigma)
                self.iterates.append(self.X_hat.copy())

        def get_result(self):
            return dict(X_hat=self.X_hat, iterates=self.iterates)
"""

SOLVER_TV = """
    from benchopt import BaseSolver
    import numpy as np

    class Solver(BaseSolver):
        name = "tv_denoise"
        requirements = ["scikit-image"]
        sampling_strategy = "callback"
        parameters = {"lam": [0.1, 0.3]}

        def set_objective(self, X_noisy):
            self.X_noisy = X_noisy
            self.iterates = []

        def run(self, cb):
            from skimage.restoration import denoise_tv_chambolle
            self.X_hat = self.X_noisy.copy()
            self.iterates = [self.X_hat.copy()]
            while cb(self):
                self.X_hat = denoise_tv_chambolle(self.X_hat, weight=self.lam)
                self.iterates.append(self.X_hat.copy())

        def get_result(self):
            return dict(X_hat=self.X_hat, iterates=self.iterates)
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

PLOT = """
    import base64
    import io

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    from benchopt import BasePlot


    def _array_to_data_uri(arr, cmap="gray"):
        fig, ax = plt.subplots(figsize=(3, 3))
        ax.imshow(arr, cmap=cmap, interpolation="nearest",
                  vmin=0, vmax=1)
        ax.axis("off")
        fig.tight_layout(pad=0)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=80, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return "data:image/png;base64," + base64.b64encode(
            buf.read()
        ).decode("ascii")


    class ReconstructionImagePlot(BasePlot):
        name = "reconstruction"
        type = "image"
        options = {"dataset": ..., "objective": ...}

        def plot(self, df, dataset, objective):
            df = df.query(
                "dataset_name == @dataset and objective_name == @objective"
            )
            images = []
            for solver_name, sdf in df.groupby("solver_name"):
                row = sdf[sdf["stop_val"] == sdf["stop_val"].max()].iloc[0]
                val = row.get("objective_value", float("nan"))
                iterates = row.get("objective_iterates", None)
                if (
                    iterates is not None
                    and not (isinstance(iterates, float) and np.isnan(iterates))
                    and len(iterates) > 0
                ):
                    src = _array_to_data_uri(np.array(iterates[-1]))
                    caption = (
                        f"Final iterate ({len(iterates)} steps), "
                        f"MSE={val:.4f}"
                    )
                else:
                    fig, ax = plt.subplots(figsize=(3, 3))
                    ax.text(0.5, 0.5, f"MSE={val:.4f}",
                            ha="center", va="center",
                            fontsize=16, transform=ax.transAxes)
                    ax.axis("off")
                    buf = io.BytesIO()
                    fig.savefig(buf, format="png", dpi=80,
                                bbox_inches="tight")
                    plt.close(fig)
                    buf.seek(0)
                    src = "data:image/png;base64," + base64.b64encode(
                        buf.read()
                    ).decode("ascii")
                    caption = f"MSE={val:.4f}"
                images.append(
                    {"src": src, "label": solver_name, "caption": caption}
                )
            return images

        def get_metadata(self, df, dataset, objective):
            n = len(df.query(
                "dataset_name == @dataset and objective_name == @objective"
            )["solver_name"].unique())
            return {
                "title": f"{objective} — Data: {dataset}",
                "ncols": min(n, 4),
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
    f"run {benchmark.benchmark_dir} -n 5 -r 1 --no-plot"
)

# %%
# In the resulting HTML page, select **reconstruction** in the *Chart type*
# dropdown to see the image grid. Each card shows the final denoised image
# produced by that solver configuration, with its MSE and number of steps.
#
# The image data is embedded as base64-encoded PNGs directly in the HTML
# file, so the page is fully self-contained.
