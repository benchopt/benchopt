from benchopt import BasePlot


class Plot(BasePlot):
    name = "Custom plot 1"
    type = "scatter"
    dropdown = {
        "dataset": ...,  # Will fetch the dataset names from the df
        "color": ["blue", "red"]
    }

    def plot(self, df, dataset, color):
        df = df[(df['dataset_name'] == dataset)]
        return [
            {
                "x": df[(df['solver_name'] == solver)]["time"].values.tolist(),
                "y": (
                    df[(df['solver_name'] == solver)]
                    ["objective_value"].values.tolist()),
                "color": color,  # possible to use the rgba instead
                "marker": "x",  # possible to give an int instead
                "label": solver,
            }
            for solver in df['solver_name'].unique()
        ]

    def get_metadata(self, df, dataset, color):
        df = df[(df['dataset_name'] == dataset)]
        title = f"Custom Plot 1\nData: {dataset}\nColor: {color}"
        return {
            "title": title,
            "xlabel": "Custom X-axis",
            "ylabel": "Custom Y-axis",
        }
