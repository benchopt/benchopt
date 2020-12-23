import matplotlib.pyplot as plt
import numpy as np
try:
    import plotly.graph_objects as go
except ImportError:
    go = None


def fill_between_x(fig, x, q1, q9, y, color, marker, label, plotly=False):
    if not plotly:
        plt.loglog(x, y, color=color, marker=marker, label=label, linewidth=3)
        plt.fill_betweenx(y, q1, q9, color=color, alpha=.3)
        return fig

    color = f'rgba{color}'
    fig.add_trace(go.Scatter(
        x=x, y=y,
        line_color=color, marker_symbol=marker, mode='lines+markers',
        name=label, legendgroup=label,
    ))
    fig.add_trace(go.Scatter(
        x=q1, y=y, mode='lines', showlegend=False,
        line={'width': 0, 'color': color}, legendgroup=label,
    ))
    fig.add_trace(go.Scatter(
        x=q9, y=y, mode='lines', fill='tonextx', showlegend=False,
        line={'width': 0, 'color': color}, legendgroup=label,
    ))

    return fig


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


def add_h_line(fig, val, xlim=None, plotly=False):
    "Add an horizontal black dash line with value val."
    if not plotly:
        plt.hlines(val, *xlim, color='k', linestyle='--')
        plt.xlim(xlim)
        return fig

    fig.add_trace(go.Scatter(
        x=xlim, y=[val] * 2,
        line_dash='dot', line_color='black',
        mode='lines', showlegend=False
    ))


def make_bars(fig, heights, ticks, width, colors, times, plotly=False):
    if not plotly:
        ax = fig.gca()
        for idx, tick in enumerate(ticks):
            xi = tick[0]
            height = heights[idx]
            edges = colors[idx] if colors[idx] != "w" else "k"
            ax.bar(x=xi, height=height, width=width,
                   color=colors[idx], edgecolor=edges)
            if colors[idx] == "w":
                ax.annotate("Did not converge", xy=(xi, height/2), ha='center',
                            va='center', color='k', rotation=90)
            else:
                plt.scatter(np.ones_like(times[idx]) * xi, times[idx],
                            marker='_', color='k', zorder=10)
    else:
        colors = [f'rgba{color}' for color in colors]
        xi, _ = zip(*ticks)
        fig.add_trace(go.Bar(x=xi, y=heights,
                             width=[width] * len(xi),
                             marker_color=colors))
        no_cv = [True if col ==
                 "rgba(0.8627, 0.8627, 0.8627)" else False for col in colors]
        if any(no_cv):
            pts = zip(list(np.array(xi)[no_cv]),
                      [h_ / 2 for h_ in np.array(heights)[no_cv]])
            fig.update_layout(annotations=[
                go.layout.Annotation(
                    x=pts_[0],
                    y=np.log(pts_[1]),
                    text="Did not converge",
                    valign="bottom",
                    textangle=-90, yanchor="middle",
                    showarrow=False) for pts_ in pts])
        for idx, x_ in enumerate(xi):
            if not no_cv[idx]:
                fig.add_trace(
                    go.Scatter(
                        mode='markers', x=np.ones_like(times[idx]) * x_,
                        y=times[idx],
                        marker=dict(color="black", symbol="line-ew-open")))
        fig.update_layout(showlegend=False)
