import matplotlib.pyplot as plt

from .helpers import get_solver_style

EPS = 1e-10


def _remove_prefix(text, prefix):
    return text[len(prefix):] if text.startswith(prefix) else text


def compute_objective_curve_data(df, obj_col='objective_value'):
    data = {}
    dropdown = {
        "Dataset": df['data_name'].unique(),
        "Objective": df['objective_name'].unique(),
        "Solver": df['solver_name'].unique(),
        "X-axis": ["Time", "Iteration"],
    }
    for dataset in df['data_name'].unique():
        for objective in df['objective_name'].unique():
            for solver in df['solver_name'].unique():
                data_filtered = df[
                    (df['data_name'] == dataset) &
                    (df['solver_name'] == solver) &
                    (df['objective_name'] == objective)
                ]
                if data_filtered.empty:
                    continue

                key_list = ["objective_curve", dataset, objective, solver]

                curve = data_filtered.groupby('stop_val').median(
                    numeric_only=True)
                q1 = data_filtered.groupby('stop_val')['time'].quantile(.1)
                q9 = data_filtered.groupby('stop_val')['time'].quantile(.9)

                color, marker = get_solver_style(solver)

                key = "_".join(key_list + ["Time"])
                data[key] = {
                    "x": curve['time'].tolist(),
                    "y": curve[obj_col].tolist(),
                    "q1": q1.tolist(),
                    "q9": q9.tolist(),
                    "color": color,
                    "marker": marker,
                    "label": solver,
                }

                key = "_".join(key_list + ["Iteration"])
                data[key] = {
                    "x": list(range(len(curve))),
                    "y": curve[obj_col].tolist(),
                    "q1": q1.tolist(),
                    "q9": q9.tolist(),
                    "color": color,
                    "marker": marker,
                    "label": solver,
                }

    return data, dropdown


def compute_solvers_objective_curve_data(df, obj_col, suboptimality, relative):
    """Compute and shape data for MANY solvers to display in objective curve"""
    df = df.copy()
    data = {}
    data["solvers"] = {}
    solver_names = df['solver_name'].unique()

    dataset_name = df['data_name'].unique()[0]
    objective_name = df['objective_name'].unique()[0]
    data["title"] = f"{objective_name}\nData: {dataset_name}"

    y_label = "F(x)"
    if suboptimality:
        y_label = "F(x) - F(x*)"
        c_star = df[obj_col].min() - EPS
        df.loc[:, obj_col] -= c_star

    if relative:
        if suboptimality:
            y_label = "F(x) - F(x*) / F(x0) - F(x*)"
        else:
            y_label = "F(x) / F(x0)"
        max_f_0 = df[df['stop_val'] == 1][obj_col].max()
        df.loc[:, obj_col] /= max_f_0
    data["y_label"] = y_label

    for solver_name in solver_names:
        df_filtered = df[df['solver_name'] == solver_name]
        data["solvers"][solver_name] = compute_solver_objective_curve_data(
            df_filtered, obj_col, solver_name
        )

    return data


def compute_solver_objective_curve_data(
    df, obj_col, solver_name, plotly=False
):
    curve = df.groupby('stop_val').median(numeric_only=True)
    q1 = df.groupby('stop_val')['time'].quantile(.1)
    q9 = df.groupby('stop_val')['time'].quantile(.9)

    color, marker = get_solver_style(solver_name, plotly=plotly)

    return {
        "x": curve['time'].tolist(),
        "y": curve[obj_col].tolist(),
        "q1": q1.tolist(),
        "q9": q9.tolist(),
        "stop_val": df.index.tolist(),
        "color": color,
        "marker": marker,
    }


def plot_objective_curve(
    df, obj_col='objective_value',
    suboptimality=False, relative=False
):
    """Plot objective curve for a given benchmark and dataset.

    Plot the objective value F(x) as a function of the time.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.
    obj_col : str
        Column to select in the DataFrame for the plot.
    suboptimality : bool
        If set to True, remove the optimal objective value F(x^*). Here the
        value of F(x^*) is taken as the smallest value reached across all
        solvers.
    relative : bool
        If set to True, scale the objective value by 1 / F_0 where F_0 is
        computed as the largest objective value accross all initialization.

    Returns
    -------
    fig : matplotlib.Figure
        The rendered figure.
    """

    data = compute_solvers_objective_curve_data(
        df, obj_col, suboptimality, relative
    )

    fig = plt.figure()

    if df[obj_col].count() == 0:  # missing values
        plt.text(0.5, 0.5, "Not Available")
        return fig

    for solver_name in data["solvers"]:
        solver_data = data["solvers"][solver_name]
        plt.loglog(
            solver_data['x'], solver_data['y'],
            color=solver_data['color'], marker=solver_data['marker'],
            label=solver_name, linewidth=3
        )

        if 'q1' in solver_data and 'q9' in solver_data:
            plt.fill_betweenx(
                solver_data['y'], solver_data["q1"], solver_data["q9"],
                color=solver_data['color'], alpha=.3
            )

    if suboptimality and not relative:
        plt.hlines(EPS, df['time'].min(), df['time'].max(), color='k',
                   linestyle='--')
        plt.xlim(df['time'].min(), df['time'].max())

    # Format the plot to be nice
    plt.legend(fontsize=14)
    plt.xlabel("Time [sec]", fontsize=14)
    plt.ylabel(f"{_remove_prefix(obj_col, 'objective_')}: {data['y_label']}",
               fontsize=14)
    plt.title(data["title"], fontsize=14)
    plt.tight_layout()

    return fig


def plot_suboptimality_curve(df, obj_col='objective_value'):
    """Plot suboptimality curve for a given benchmark and dataset.

    Plot suboptimality, that is F(x) - F(x^*) as a function of time,
    where F(x^*) is the smallest value reached in df.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.
    obj_col : str
        Column to select in the DataFrame for the plot.

    Returns
    -------
    fig : instance of matplotlib.figure.Figure
        The matplotlib figure.
    """
    return plot_objective_curve(df, obj_col=obj_col, suboptimality=True)


def plot_relative_suboptimality_curve(df, obj_col='objective_value'):
    """Plot relative suboptimality curve for a given benchmark and dataset.

    Plot relative suboptimality, that is (F(x) - F(x*)) / (F_0 - F(x*)) as a
    function of the time, where F(x*) is the smallest value reached in df and
    F_0 the largest initial loss across all solvers.

    Parameters
    ----------
    df : instance of pandas.DataFrame
        The benchmark results.
    obj_col : str
        Column to select in the DataFrame for the plot.

    Returns
    -------
    fig : instance of matplotlib.figure.Figure
        The matplotlib figure.
    """
    return plot_objective_curve(df, obj_col=obj_col, suboptimality=True,
                                relative=True)


def compute_quantiles(df_filtered):
    q1 = df_filtered.groupby('stop_val')['time'].quantile(.1)
    q9 = df_filtered.groupby('stop_val')['time'].quantile(.9)

    return q1, q9
