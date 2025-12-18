from benchopt import BasePlot


class Plot(BasePlot):
    name = "Example table"
    type = "table"
    dropdown = {}

    def plot(self, df):
        plots = []
        for solver in df['solver_name'].unique():
            solver_df = df[df['solver_name'] == solver]
            # Get the final objective value and time for each solver
            final_objective = float(
                solver_df.select_dtypes(include=['number'])
                .groupby('stop_val')
                .median()["objective_value"]
                .values[-1]
            )
            final_time = float(
                solver_df.select_dtypes(include=['number'])
                .groupby('stop_val')
                .median()
                .index[-1]
            )
            plots.append([solver, final_objective, final_time])
        return plots

    def get_metadata(self, df):
        return {
            "title": "Comparison of solvers",
            "columns": ["solver", "value", "time"],
        }
