import matplotlib.pyplot as plt


def get_figures(benchmark, df, output_dir, kinds):
    "Get the matplotlib figures of the avaible custom plots"
    figs = []
    for plot in benchmark.get_custom_plots():
        #  TODO check if kinds specified exist
        if plot._get_name() not in kinds:
            continue
        figs.extend(get_plot_figures(plot, df, output_dir))
    return figs


def get_plot_figures(plot, df, output_dir):
    if plot.type == "scatter":
        return get_plot_scatter(plot, df, output_dir)
    else:
        raise NotImplementedError(
            f"Plot type {plot.type} not implemented for matplotlib."
        )


def get_plot_scatter(plot, df, output_dir):
    df = df.copy()
    data, _ = plot._get_all_plots(df)
    figs = []
    for key, plot_datas in data.items():

        fig = plt.figure()
        for plot_data in plot_datas["data"]:
            color, marker = plot.get_style(
                plot_data["label"], plotly=False
            )  # TODO change this
            plt.loglog(
                plot_data["x"], plot_data["y"], color=color,
                marker=marker, label=plot_data["label"],
                linewidth=3
            )

            if "q1" in plot_data and "q9" in plot_data:
                q1 = plot_data["q1"]
                q9 = plot_data["q9"]
                plt.fill_betweenx(
                    plot_data["y"], q1, q9, color=plot_data["color"],
                    alpha=.3
                )

        # Format the plot to be nice
        plt.legend(fontsize=14)
        plt.xlabel(plot_datas["xlabel"], fontsize=14)
        plt.ylabel(plot_datas["ylabel"], fontsize=14)
        plt.title(plot_datas["title"], fontsize=14)
        plt.tight_layout()

        save_name = output_dir / f"{key}"
        if hasattr(fig, 'write_html'):
            save_name = save_name.with_suffix('.html')
            fig.write_html(str(save_name), include_mathjax='cdn')
        else:
            save_name = save_name.with_suffix('.pdf')
            plt.savefig(save_name)
        print(f'Save {key} as: {save_name}')
        figs.append(fig)

    return figs
