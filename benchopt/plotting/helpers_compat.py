import matplotlib.pyplot as plt
import numpy as np
try:
    import plotly.graph_objects as go
except ImportError:
    go = None


def get_figure(plotly=False):
    "Get matplotlib or plotly figure in a compatible way"

    if not plotly:
        return plt.figure()

    if go is None:
        raise ValueError(
            "Need to install plotly to use option `--plotly`.\n"
            "Please run `pip install plotly`."
        )
    return go.Figure()


def _make_bars(fig, heights, ticks, width, colors, times, plotly=False):
    if not plotly:
        ax = fig.gca()
        for idx, tick in enumerate(ticks):
            no_cv = np.isnan(times[idx]).any()
            xi = tick[0]
            height = heights[idx]
            edges = colors[idx] if not no_cv else "k"
            ax.bar(x=xi, height=height, width=width,
                   color=colors[idx], edgecolor=edges)
            if no_cv:
                ax.text(xi, .5, "Did not converge",
                        ha="center", va="center", color='k',
                        rotation=90, transform=ax.transAxes)
            else:
                plt.scatter(np.ones_like(times[idx]) * xi, times[idx],
                            marker='_', color='k', zorder=10)
    else:
        colors = [f'rgba{color}' for color in colors]
        xi, _ = zip(*ticks)
        text_ = ["Did not converge" if np.isnan(
            time).any() else " " for time in times]
        fig.add_trace(go.Bar(x=xi,
                             y=heights,
                             width=[width],
                             marker_color=colors,
                             text=text_,
                             textposition="inside",
                             insidetextanchor='middle',
                             textangle=-90))
        for idx, x_ in enumerate(xi):
            if text_[idx] == " ":
                fig.add_trace(
                    go.Scatter(
                        mode='markers', x=np.ones_like(times[idx]) * x_,
                        y=times[idx],
                        marker=dict(color="black", symbol="line-ew-open")))
        fig.update_layout(showlegend=False)
