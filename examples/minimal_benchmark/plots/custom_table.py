from benchopt import BasePlot


class Plot(BasePlot):
    name = "Example table"
    type = "table"
    dropdown = {}

    def plot(self, df):
        plots = []

        # Get numeric columns starting with 'objective_'
        df_filtered = df.select_dtypes(include=['number']).columns
        objective_cols = [
            col for col in df_filtered if col.startswith('objective_')
        ]

        for solver in df['solver_name'].unique():
            solver_res = [solver]
            solver_df = df[df['solver_name'] == solver]
            for col in objective_cols:
                if col not in solver_df.columns:
                    continue
                median_val = float(
                    solver_df.select_dtypes(include=['number'])
                    .groupby('stop_val')
                    .median()[col]
                    .values[-1]
                )
                solver_res.append(median_val)

            final_time = float(
                solver_df.select_dtypes(include=['number'])
                .groupby('stop_val')
                .median()['time']
                .values[-1]
            )
            solver_res.append(final_time)
            plots.append(solver_res)
        return plots

    def get_metadata(self, df):
        df_filtered = df.select_dtypes(include=['number']).columns
        objective_cols = [
            col for col in df_filtered if col.startswith('objective_')
        ]
        columns = ["solver"] + objective_cols + ["time (s)"]
        return {
            "title": "Comparison of solvers",
            "columns": columns,
        }
