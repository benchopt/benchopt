from hashlib import md5
import matplotlib.pyplot as plt
import matplotlib

from .base import BasePlot

CMAP = plt.get_cmap('tab20')
COLORS = [CMAP(i) for i in range(CMAP.N)]
COLORS = COLORS[::2] + COLORS[1::2]
MARKERS = {i: v for i, v in enumerate(plt.Line2D.markers)}
MARKERS_STR = {v: i for i, v in MARKERS.items()}


def reset_solver_styles():
    BasePlot.label_dict.clear()


def get_plot_id(benchmark, df):
    hasher = md5()

    # Hash benchmark, dataset, objective and solver names in the benchmark
    hasher.update(benchmark.encode('utf-8'))  # benchmark
    hasher.update(df['dataset_name'].unique()[0].encode('utf-8'))
    hasher.update(df['objective_name'].unique()[0].encode('utf-8'))
    for s in df['solver_name'].unique():
        hasher.update(s.encode('utf-8'))
    max_n_rep = df['idx_rep'].max()
    max_stop_val = df['stop_val'].max()
    min_stop_val = df['stop_val'].min()
    hasher.update(f'{max_n_rep} {max_stop_val} {min_stop_val}'.encode('utf-8'))
    plot_id = hasher.hexdigest()
    return plot_id


def update_plot_data_style(plot_data, plotly=True):
    """Update the color and marker of each trace in the plot data."""
    custom_data = {**plot_data}
    for plot_name in custom_data:
        for key in custom_data[plot_name]:
            if plotly:
                title = custom_data[plot_name][key]["title"]
                title = title.replace('\n', '<br />')
                custom_data[plot_name][key]["title"] = title

            data = custom_data[plot_name][key]["data"]
            for idx in range(len(data)):
                if "marker" in data[idx]:
                    marker = data[idx]["marker"]

                    if plotly and isinstance(marker, str):
                        marker = MARKERS_STR[marker]
                    elif not plotly and isinstance(marker, int):
                        marker = MARKERS[marker % len(MARKERS)]

                    custom_data[plot_name][key]["data"][idx]["marker"] = marker

                if "color" in data[idx] and plotly:
                    color = data[idx]["color"]
                    if isinstance(color, str):
                        color = matplotlib.colors.to_rgba(color)
                    color = tuple(
                        int(255*x) if i != 3 else float(x)
                        for i, x in enumerate(color)
                    )
                    custom_data[plot_name][key]["data"][idx]["color"] = \
                        f"rgba{color}"

    return custom_data
