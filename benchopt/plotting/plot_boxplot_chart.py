def compute_boxplot_data(df, obj_col):
    """Compute and shape data to display in boxplot"""

    """By SOLVERS : Compute final time and final objective_value data"""
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

    """By ITERATIONS : Compute time and objective_value"""
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
