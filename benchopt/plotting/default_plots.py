import numpy as np

from .base import BasePlot


EPS = 1e-8


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
        df = df[df['dataset_name'] == dataset]
        df = df[df['objective_name'] == objective]

        plots = []
        for solver in df['solver_name'].unique():
            df_filtered = (
                df[df['solver_name'] == solver]
                .select_dtypes(include=['number'])
                .groupby('stop_val')
            )
            df_filtered_median = df_filtered.median()
            if objective_column not in df_filtered_median:
                continue
            y = (
                df_filtered_median[objective_column]
                .values.tolist()
            )
            x = df_filtered_median["time"].values.tolist()
            if X_axis == "Iteration":
                x = df_filtered_median.index.tolist()

            curve_data = {
                "x": x,
                "y": y,
                "label": solver,
                **self.get_style(solver)
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
        df = df[df['dataset_name'] == dataset]
        df = df[df['objective_name'] == objective]
        # TODO use br
        title = f"{objective}\nData: {dataset} "
        return {
            "title": title,
            "xlabel": X_axis,
            "ylabel": "Objective Value",
        }


class BarChart(BasePlot):
    name = "bar_chart"
    type = "bar_chart"
    dropdown = {
        "dataset": ...,
        "objective": ...,
        "objective_column": ...,
    }

    def plot(self, df, dataset, objective, objective_column):
        df = df[(df['dataset_name'] == dataset)]
        df = df[(df['objective_name'] == objective)]

        plots = []
        for solver in df['solver_name'].unique():
            df_filtered = df[(df['solver_name'] == solver)]
            c_star = df_filtered[objective_column].min() + EPS
            df_tol = df_filtered.groupby('stop_val').filter(
                lambda x: x[objective_column].max() < c_star)

            if df_tol.empty:
                text = 'Did not converge'
                height = df.time.max()
                times = np.nan
            else:
                stop_val = df_tol['stop_val'].min()
                this_df = df_filtered[df_filtered['stop_val'] == stop_val]
                text = ''
                height = this_df['time'].median()
                times = this_df['time'].tolist()

            plots.append({
                "y": height,
                "times": times,
                "text": text,
                "label": solver,
                "color": self.get_style(solver)["color"]
            })

        return plots

    def get_metadata(self, df, dataset, objective, objective_column):
        return {
            "title": f"{objective}\nData: {dataset}",
            "ylabel": "Time [sec]",
        }
