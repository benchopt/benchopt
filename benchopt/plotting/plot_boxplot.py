import matplotlib.pyplot as plt

from benchopt.plotting.plot_objective_curve import get_solver_style


def plot_boxplot(df, obj_col='objective_value', plotly=False):
    solvers, data, colors = compute_solvers_boxplot_data(df, obj_col)
    dataset_name = df['data_name'].unique()[0]
    objective_name = df['objective_name'].unique()[0]

    fig, ax = plt.subplots()

    boxplot = plt.boxplot(data, labels=solvers, patch_artist=True)

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


def compute_solvers_boxplot_data(df, obj_col):
    """Compute and shape data for MANY solvers to display in boxplot"""
    data, colors = list(), list()
    solver_names = df['solver_name'].unique()

    for solver_name in solver_names:
        col, _ = get_solver_style(solver_name, plotly=False)
        colors.append(col)
        df_filtered = df.query('solver_name == @solver_name')
        data.append(
            compute_solver_boxplot_data(
                df_filtered, obj_col
            )["by_solver"]["final_objective_value"]
        )

    return solver_names, data, colors


def compute_solver_boxplot_data(df, obj_col):
    """Compute and shape data for ONE solver to display in boxplot

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results for one solver.
    obj_col : str
        Column to select in the DataFrame for the plot.

    Returns
    -------
    dict : data to construct the boxplots in JS per solver or iterations.
    """

    # By SOLVERS : Compute final time and final objective_value data
    boxplot_by_solver = dict(
        final_times=(
            df[['idx_rep', 'time']]
            .groupby('idx_rep')['time']
            .max()
        ).tolist(),
        final_objective_value=(
            df[['idx_rep', obj_col]]
            .groupby('idx_rep')[obj_col]
            .min()
        ).tolist()
    )

    # By ITERATIONS : Compute time and objective_value per iteration
    max_iteration = df['idx_rep'].value_counts().max()
    # Arrays to keep data to send to html
    times = [[] for i in range(max_iteration)]
    objective_metric_values = [[] for i in range(max_iteration)]
    # For each repetition
    for i in range(df['idx_rep'].max() + 1):
        tmp_time = df.query('idx_rep == @i')['time'].tolist()
        tmp_objective_metric_value = (
            df.query('idx_rep == @i')[obj_col].tolist()
        )
        # For each iteration
        for j in range(len(tmp_time)):
            times[j].append(tmp_time[j])
            objective_metric_values[j].append(tmp_objective_metric_value[j])

    boxplot_by_iteration = dict(
        times=times,
        objective=objective_metric_values,
    )

    return {
        'by_solver': boxplot_by_solver,
        'by_iteration': boxplot_by_iteration
    }
