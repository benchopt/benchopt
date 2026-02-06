from benchopt import BasePlot


class Plot(BasePlot):
    name = "Custom plot 1"
    type = "scatter"
    options = {
        "dataset": ...,  # Will fetch the dataset names from the df
        "color": ["blue", "red"]
    }

    def plot(self, df, dataset, color):
        df = df[(df['dataset_name'] == dataset)]
        return [
            {
                "y": (
                    df[df['solver_name'] == solver]
                    .select_dtypes(include=['number'])
                    .groupby('stop_val')
                    .median()["objective_value"]
                    .values.tolist()
                ),
                "x": (
                    df[df['solver_name'] == solver]
                    .select_dtypes(include=['number'])
                    .groupby('stop_val')
                    .median()
                    .index.tolist()
                ),
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
