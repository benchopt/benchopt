import matplotlib.pyplot as plt
import numpy as np

from .helpers import update_plot_data_style
import warnings


def get_figures(benchmark, df, output_dir, kinds):
    "Get the matplotlib figures of the avaible custom plots"
    figs = []
    plot_data, _ = benchmark.get_plot_data(df, kinds)
    plot_data = update_plot_data_style(plot_data, plotly=False)
    for plot_name in plot_data.keys():
        if plot_name not in kinds:
            continue
        figs.append(get_plot_figure(plot_data[plot_name], output_dir))
    return figs


def get_plot_figure(plot_datas, output_dir):
    figs = []
    for key, plot_data in plot_datas.items():
        if plot_data["type"] == "scatter":
            fig = get_plot_scatter(plot_data)
        elif plot_data["type"] == "bar_chart":
            fig = get_plot_barchart(plot_data)
        elif plot_data["type"] == "boxplot":
            fig = get_plot_boxplot(plot_data)
        elif plot_data["type"] == "table":
            warnings.warn(
                f"Plot '{key}' (type 'table') cannot be "
                f"rendered with matplotlib; skipping.",
                UserWarning
            )
            continue
        else:
            raise NotImplementedError(
                f"Plot type {plot_data['type']} "
                f"not implemented for matplotlib."
            )
        save_name = output_dir / f"{key}"
        save_name = save_name.with_suffix('.pdf')
        fig.savefig(save_name)
        print(f'Save {key} as: {save_name}')
        figs.append(fig)
    return figs


def get_plot_scatter(plot_data):
    fig = plt.figure()
    for curve_data in plot_data["data"]:
        plt.loglog(
            curve_data["x"], curve_data["y"], color=curve_data["color"],
            marker=curve_data["marker"], label=curve_data["label"],
            linewidth=3
        )

        if "x_low" in curve_data and "x_high" in curve_data:
            x_low = curve_data["x_low"]
            x_high = curve_data["x_high"]
            plt.fill_betweenx(
                curve_data["y"], x_low, x_high, color=curve_data["color"],
                alpha=.3
            )

    # Format the plot to be nice
    plt.legend(fontsize=14)
    plt.xlabel(plot_data["xlabel"], fontsize=14)
    plt.ylabel(plot_data["ylabel"], fontsize=14)
    plt.title(plot_data["title"], fontsize=14)
    plt.tight_layout()

    return fig


def get_plot_barchart(plot_data):
    fig = plt.figure()
    n_bars = len(plot_data["data"])

    width = 1 / (n_bars + 2)
    colors = []

    val_list = []

    for i, bar_data in enumerate(plot_data["data"]):
        colors.append(bar_data["color"])
        val_list.append(bar_data["y"])

    ax = fig.gca()

    for idx in range(n_bars):
        no_cv = np.isnan(val_list[idx]).any()
        xi = (idx+1.5)*width
        height = np.median(val_list[idx])
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
                np.ones_like(val_list[idx]) * xi, val_list[idx],
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

    return fig


def get_plot_boxplot(plot_data):
    fig = plt.figure()

    # collect the union of all labels (x tick names)
    all_labels = []
    for d in plot_data["data"]:
        for x in d["x"]:
            if x not in all_labels:
                all_labels.append(x)

    for data in plot_data["data"]:
        # all datasets with the same label stack on the *exact* same x
        positions = [all_labels.index(x) for x in data["x"]]

        boxplot = plt.boxplot(
            data["y"],
            positions=positions,
            widths=0.6,           # you can keep this fixed
            patch_artist=True,
        )

        color = data["color"]
        for box in boxplot["boxes"]:
            box.set(color=color, linewidth=1, alpha=0.7)
            box.set_facecolor(color)
        for median in boxplot["medians"]:
            median.set(color=color, linewidth=1)
        for whisker in boxplot["whiskers"]:
            whisker.set(color=color, linewidth=1)
        for flier in boxplot["fliers"]:
            flier.set(color=color)

    plt.xticks(range(len(all_labels)), all_labels, rotation=45)
    plt.title(plot_data["title"])
    plt.ylabel(plot_data["ylabel"])

    return fig
