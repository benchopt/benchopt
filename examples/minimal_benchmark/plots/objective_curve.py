from benchopt import BasePlot


class Plot(BasePlot):
    name = "Objective Curve"
    type = "scatter"
    dropdown = {
        "dataset": ...,
        "objective": ...,
        "X_axis": ["Time", "Iteration"],
    }

    def plot(self, df, dataset, objective, X_axis):
        df = df[df['data_name'] == dataset]
        df = df[df['objective_name'] == objective]
        x = df["time"].values.tolist()
        if X_axis == "Iteration":
            x = list(range(len(x)))
        return [
            {
                "x": x,
                "y": (
                    df[(df['solver_name'] == solver)]
                    ["objective_value"].values.tolist()),
                "color": self.get_style(solver)[0],
                "marker": self.get_style(solver)[1],
                "label": solver,
            }
            for solver in df['solver_name'].unique()
        ]

    def get_metadata(self, df, dataset, objective, X_axis):
        df = df[df['data_name'] == dataset]
        df = df[df['objective_name'] == objective]
        title = f"Objective Curve\nData: {dataset}\nObjective: {objective}"
        return {
            "title": title,
            "xlabel": X_axis,
            "ylabel": "Objective Value",
        }
