import matplotlib.pyplot as plt

from .helpers import update_plot_data_style


def get_figures(benchmark, df, output_dir, kinds):
    "Get the matplotlib figures of the avaible custom plots"
    figs = []
    plot_data, _ = benchmark.get_plot_data(df)
    plot_data = update_plot_data_style(plot_data, plotly=False)
    for plot_name in plot_data.keys():
        if plot_name not in kinds:
            continue
        figs.append(get_plot_figure(plot_data[plot_name], df, output_dir))
    return figs


def get_plot_figure(plot_datas, df, output_dir):
    for key, plot_data in plot_datas.items():
        if plot_data["type"] == "scatter":
            return get_plot_scatter(key, plot_data, df, output_dir)
        else:
            raise NotImplementedError(
                f"Plot type {plot_data['type']} "
                f"not implemented for matplotlib."
            )


def get_plot_scatter(key, plot_data, df, output_dir):
    df = df.copy()

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
    if hasattr(fig, 'write_html'):
        save_name = save_name.with_suffix('.html')
        fig.write_html(str(save_name), include_mathjax='cdn')
    else:
        save_name = save_name.with_suffix('.pdf')
        plt.savefig(save_name)
    print(f'Save {key} as: {save_name}')

    return fig
