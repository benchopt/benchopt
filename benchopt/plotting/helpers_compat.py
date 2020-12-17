import matplotlib.pyplot as plt
try:
    import plotly.graph_objects as go
except ImportError:
    go = None


def fill_between_x(fig, x, q1, q9, y, color, label, plotly=False):

    if not plotly:
        plt.loglog(x, y, color, label=label, linewidth=3)
        plt.fill_betweenx(y, q1, q9, color=color, alpha=.3)
        return fig

    color = f'rgba{color}'
    fig.add_trace(go.Scatter(
        x=x, y=y,
        line_color=color, mode='lines',
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

    fig.add_trace(go.Scatter(
        x=xlim, y=[val] * 2,
        line_dash='dot', line_color='black',
        mode='lines', showlegend=False
    ))
