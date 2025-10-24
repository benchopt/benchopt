import matplotlib.pyplot as plt


# TODO remove
def plot_boxplot(df, obj_col='objective_value', plotly=False):
    solvers, data, colors = [], [], []
    dataset_name = df['dataset_name'].unique()[0]
    objective_name = df['objective_name'].unique()[0]

    fig, ax = plt.subplots()

    boxplot = plt.boxplot(data, tick_labels=solvers, patch_artist=True)

    for box, color in zip(boxplot['boxes'], colors):
        box.set(color=color, linewidth=1, alpha=0.7)
        box.set_facecolor(color)

    for median, color in zip(boxplot['medians'], colors):
        median.set(color=color, linewidth=1)

    for whisker, color in zip(boxplot['whiskers'], colors):
        whisker.set(color=color, linewidth=1)

    for flier, color in zip(boxplot['fliers'], colors):
        flier.set(color=color)

    plt.title(f"{objective_name}\nData: {dataset_name}")
    plt.xticks(rotation=45)
    plt.ylabel(obj_col)

    return fig
