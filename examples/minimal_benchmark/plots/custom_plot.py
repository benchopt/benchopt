from benchopt import BasePlot


class Plot(BasePlot):
    name = "Custom plot 1"
    params = {
        "dataset": ...,  # Will fetch the dataset names from the df
        "color": ["blue", "red"]
    }

    def plot(self, df, dataset, color):
        df = df[(df['data_name'] == dataset)]
        data = [
            {
                "x": df["time"].values.tolist(),
                "y": (
                    df[(df['solver_name'] == solver)]
                    ["objective_value"].values.tolist()),
                "color": color,
                "marker": "circle",
                "label": solver,
            }
            for solver in df['solver_name'].unique()
        ]
        return {
            "title": "Example plot",
            "x_label": "custom time",
            "y_label": "custom objective value",
            "data": data
        }
