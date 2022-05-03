# We define this mapping here to allow bash completion without needing to
# import the plotting libraries.

PLOT_KINDS = {
    'objective': 'plot_objective_curve',
    'sub_optimality': 'plot_suboptimality_curve',
    'relative_suboptimality': 'plot_relative_suboptimality_curve',
    'sub_optimality_per_iteration': 'plot_iteration_suboptimality_curve',
    'objective_per_iteration': 'plot_iteration_curve',
    'bar_chart': 'plot_bar_chart',
}
