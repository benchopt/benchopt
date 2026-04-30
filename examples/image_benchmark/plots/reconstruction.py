"""Custom image plot for the image-denoising benchmark.

Shows the final reconstructed image of every solver side-by-side,
together with the noisy input and (if the objective column carries
``iterates``) optional per-solver snapshots.
"""
import base64
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from benchopt import BasePlot


def _array_to_data_uri(arr, vmin=None, vmax=None, cmap="gray"):
    """Convert a 2-D float array to a PNG base64 data-URI string."""
    fig, ax = plt.subplots(figsize=(3, 3))
    ax.imshow(arr, cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest")
    ax.axis("off")
    fig.tight_layout(pad=0)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=80, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


class ReconstructionImagePlot(BasePlot):
    """Display the final reconstruction of each solver as an image grid.

    The ``objective_column`` option is intentionally left as ``...``
    so benchopt fills it automatically from the result columns.
    The plot is most useful with columns that carry array data; for
    scalar columns it falls back to a text-card.
    """

    name = "reconstruction"
    type = "image"

    options = {
        "dataset": ...,
        "objective": ...,
    }

    def plot(self, df, dataset, objective):
        df = df.query(
            "dataset_name == @dataset and objective_name == @objective"
        )

        images = []

        for solver_name, solver_df in df.groupby("solver_name"):
            # Take the row at the last stop_val (best iterate)
            last_stop = solver_df["stop_val"].max()
            row = solver_df[solver_df["stop_val"] == last_stop].iloc[0]

            # Try to retrieve stored iterates from the objective column.
            # The objective stores them under "objective_iterates".
            iterate_col = "objective_iterates"
            if iterate_col in solver_df.columns:
                iterates = row[iterate_col]
            else:
                iterates = None

            if (
                iterates is not None
                and not (
                    isinstance(iterates, float) and np.isnan(iterates)
                )
                and len(iterates) > 0
            ):
                arr = np.array(iterates[-1])
                src = _array_to_data_uri(arr)
                caption = (
                    f"Final iterate ({len(iterates)} steps), "
                    f"MSE={row.get('objective_value', float('nan')):.4f}"
                )
            else:
                # Fall back: render the scalar objective value as text
                val = row.get("objective_value", "n/a")
                fig, ax = plt.subplots(figsize=(3, 3))
                ax.text(
                    0.5, 0.5,
                    f"MSE\n{val:.4f}" if isinstance(val, float) else str(val),
                    ha="center", va="center",
                    fontsize=18, transform=ax.transAxes,
                )
                ax.axis("off")
                buf = io.BytesIO()
                fig.savefig(buf, format="png", dpi=80, bbox_inches="tight")
                plt.close(fig)
                buf.seek(0)
                b64 = base64.b64encode(buf.read()).decode("ascii")
                src = f"data:image/png;base64,{b64}"
                caption = f"MSE={val:.4f}"

            images.append({
                "src": src,
                "label": solver_name,
                "caption": caption,
            })

        return images

    def get_metadata(self, df, dataset, objective):
        ncols = min(
            len(df.query(
                "dataset_name == @dataset and objective_name == @objective"
            )["solver_name"].unique()),
            4,
        )
        return {
            "title": f"{objective} — Data: {dataset}",
            "ncols": ncols,
        }
