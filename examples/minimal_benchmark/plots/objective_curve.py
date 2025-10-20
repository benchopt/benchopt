from benchopt import BasePlot


class Plot(BasePlot):
    name = "Objective Curve"
    type = "scatter"
    title = "Objective Curve"
    xlabel = "Time"
    ylabel = "Objective Value"
    dropdown = {
        "dataset": ...,
        "objective": ...,
    }

    def plot(self, df, dataset, objective):
        df = df[df['data_name'] == dataset]
        df = df[df['objective_name'] == objective]
        return [
            {
                "x": df["time"].values.tolist(),
                "y": (
                    df[(df['solver_name'] == solver)]
                    ["objective_value"].values.tolist()),
                "color": self.get_style(solver)[0],
                "marker": self.get_style(solver)[1],
                "label": solver,
            }
            for solver in df['solver_name'].unique()
        ]
