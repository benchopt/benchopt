from .base import BasePlot


class ObjectiveCurvePlot(BasePlot):
    name = "Objective Curve"
    type = "scatter"
    dropdown = {
        "dataset": ...,
        "objective": ...,
        "objective_column": ...,
        "X_axis": ["Time", "Iteration"],
    }

    def plot(self, df, dataset, objective, objective_column, X_axis):
        df = df[df['data_name'] == dataset]
        df = df[df['objective_name'] == objective]

        plots = []
        for solver in df['solver_name'].unique():
            df_filtered = (
                df[df['solver_name'] == solver]
                .select_dtypes(include=['number'])
                .groupby('stop_val')
            )
            if objective_column not in df_filtered:
                continue
            y = (
                df_filtered[objective_column]
                .median().values.tolist()
            )
            x = df_filtered["time"].median().values.tolist()
            if X_axis == "Iteration":
                x = df_filtered["time"].median().index.tolist()

            curve_data = {
                "x": x,
                "y": y,
                "color": self.get_style(solver)[0],
                "marker": self.get_style(solver)[1],
                "label": solver,
            }

            if X_axis == "Time":
                curve_data['q1'] = (
                    df_filtered["time"].quantile(.1).values.tolist()
                )
                curve_data['q9'] = (
                    df_filtered["time"].quantile(.9).values.tolist()
                )

            plots.append(curve_data)

        return plots

    def get_metadata(self, df, dataset, objective, objective_column, X_axis):
        df = df[df['data_name'] == dataset]
        df = df[df['objective_name'] == objective]
        title = f"Objective Curve\nData: {dataset}\nObjective: {objective}"
        return {
            "title": title,
            "xlabel": X_axis,
            "ylabel": "Objective Value",
        }
