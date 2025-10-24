import matplotlib.pyplot as plt
import numpy as np

from .helpers import update_plot_data_style


def get_figures(benchmark, df, output_dir, kinds):
    "Get the matplotlib figures of the avaible custom plots"
    figs = []
    plot_data, _ = benchmark.get_plot_data(df)
    plot_data = update_plot_data_style(plot_data, plotly=False)
    for plot_name in plot_data.keys():
        if plot_name not in kinds:
            continue
        figs.append(get_plot_figure(plot_data[plot_name], output_dir))
    return figs


def get_plot_figure(plot_datas, output_dir):
    for key, plot_data in plot_datas.items():
        if plot_data["type"] == "scatter":
            return get_plot_scatter(key, plot_data, output_dir)
        if plot_data["type"] == "bar_chart":
            return get_plot_barchart(key, plot_data, output_dir)
        raise NotImplementedError(
            f"Plot type {plot_data['type']} "
            f"not implemented for matplotlib."
        )


def get_plot_scatter(key, plot_data, output_dir):
    fig = plt.figure()
    for curve_data in plot_data["data"]:
        plt.loglog(
            curve_data["x"], curve_data["y"], color=curve_data["color"],
            marker=curve_data["marker"], label=curve_data["label"],
            linewidth=3
        )

        if "q1" in curve_data and "q9" in curve_data:
            q1 = curve_data["q1"]
            q9 = curve_data["q9"]
            plt.fill_betweenx(
                curve_data["y"], q1, q9, color=curve_data["color"],
                alpha=.3
            )

    # Format the plot to be nice
    plt.legend(fontsize=14)
    plt.xlabel(plot_data["xlabel"], fontsize=14)
    plt.ylabel(plot_data["ylabel"], fontsize=14)
    plt.title(plot_data["title"], fontsize=14)
    plt.tight_layout()

    save_name = output_dir / f"{key}"
    save_name = save_name.with_suffix('.pdf')
    plt.savefig(save_name)
    print(f'Save {key} as: {save_name}')

    return fig


def get_plot_barchart(key, plot_data, output_dir):
    fig = plt.figure()
    n_bars = len(plot_data["data"])

    width = 1 / (n_bars + 2)
    colors = []

    height_list = []
    times_list = []

    for i, bar_data in enumerate(plot_data["data"]):
        colors.append(bar_data["color"])
        height_list.append(bar_data["y"])
        times_list.append(bar_data["times"])

    ax = fig.gca()

    for idx in range(n_bars):
        no_cv = np.isnan(times_list[idx]).any()
        xi = (idx+1.5)*width
        height = height_list[idx]
        edges = colors[idx] if not no_cv else "k"
        ax.bar(
            x=xi, height=height, width=width,
            color=colors[idx], edgecolor=edges
        )
        if no_cv:
            ax.text(
                i, .5, "Did not converge",
                ha="center", va="center", color='k',
                rotation=90, transform=ax.transAxes
            )
        else:
            plt.scatter(
                np.ones_like(times_list[idx]) * xi, times_list[idx],
                marker='_', color='k', zorder=10
            )

    ax.set_xticks([(i+1.5)*width for i in range(n_bars)])
    ax.set_xticklabels(
        [data["label"] for data in plot_data["data"]],
        rotation=60
    )
    ax.set_yscale('log')
    ax.set_xlim(0, 1)
    ax.set_ylabel(plot_data["ylabel"])
    ax.set_title(plot_data["title"], fontsize=12)
    fig.tight_layout()

    save_name = output_dir / f"{key}"
    save_name = save_name.with_suffix('.pdf')
    plt.savefig(save_name)
    print(f'Save {key} as: {save_name}')

    return fig
