from benchopt import BasePlot


class Plot(BasePlot):
    name = "Custom plot 1"
    type = "scatter"
    dropdown = {
        "dataset": ...,  # Will fetch the dataset names from the df
        "color": ["blue", "red"]
    }

    def plot(self, df, dataset, color):
        df = df[(df['data_name'] == dataset)]
        return [
            {
                "x": df[(df['solver_name'] == solver)]["time"].values.tolist(),
                "y": (
                    df[(df['solver_name'] == solver)]
                    ["objective_value"].values.tolist()),
                "color": [0, 0, 1, 1] if color == "blue" else [1, 0, 0, 1],
                "marker": 0,
                "label": solver,
            }
            for solver in df['solver_name'].unique()
        ]

    def get_metadata(self, df, dataset, color):
        df = df[(df['data_name'] == dataset)]
        title = f"Custom Plot 1\nData: {dataset}\nColor: {color}"
        return {
            "title": title,
            "xlabel": "Custom X-axis",
            "ylabel": "Custom Y-axis",
        }
