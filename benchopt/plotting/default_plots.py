from .base import BasePlot

EPS = 1e-8


class ObjectiveCurvePlot(BasePlot):
    name = "objective_curve"
    type = "scatter"
    options = {
        "dataset": ...,
        "objective": ...,
        "objective_column": ...,
        "X_axis": ["Time", "Iteration"],
    }

    def plot(self, df, dataset, objective, objective_column, X_axis):
        plots = []
        # If the column is not numeric, exit early
        from pandas.api.types import is_numeric_dtype
        if not is_numeric_dtype(df[objective_column]):
            return plots

        df = df.query(
            "dataset_name == @dataset and objective_name == @objective"
        )

        for solver, df_filtered in df.groupby('solver_name'):

            # Make sure that median value is computed with all runs.
            df_fill = (
                df_filtered.pivot_table(
                    index='stop_val',
                    columns='idx_rep',
                    values=[objective_column],
                    # should only have one value of each config
                    aggfunc="last"
                ).ffill()
                .unstack()
            )

            y = df_fill.groupby('stop_val').median(numeric_only=True)
            if X_axis == "Iteration":
                x = y.index
            else:
                x = df_filtered.groupby('stop_val')['time'].median()

            curve_data = {
                "x": x.tolist(),
                "y": y.tolist(),
                "label": solver,
                **self.get_style(solver)
            }

            if X_axis == "Time":
                # Compute the quantiles for runtime
                q = (
                    df_filtered.groupby('stop_val')['time'].quantile([.2, .8])
                    .unstack()
                )
                curve_data['x_low'] = q[.2].tolist()
                curve_data['x_high'] = q[.8].tolist()

            plots.append(curve_data)

        return plots

    def get_metadata(self, df, dataset, objective, objective_column, X_axis):
        df = df[df["dataset_name"] == dataset]
        df = df[df['objective_name'] == objective]
        title = f"{objective}\nData: {dataset} "
        return {
            "title": title,
            "xlabel": X_axis,
            "ylabel": "Objective Value",
        }


class BarChart(BasePlot):
    name = "bar_chart"
    type = "bar_chart"
    options = {
        "dataset": ...,
        "objective": ...,
        "objective_column": ...,
        "minimize": [True, False],
    }

    def plot(self, df, dataset, objective, objective_column, minimize):
        df = df.query(
            "dataset_name == @dataset and objective_name == @objective"
        )

        plots = []
        for solver, df_filtered in df.groupby('solver_name'):
            df_filtered = df_filtered.select_dtypes(include=['number'])
            if objective_column not in df_filtered:
                continue
            if minimize:
                c_star = df_filtered[objective_column].min() + EPS
                df_tol = df_filtered.groupby('stop_val').filter(
                    lambda x: x[objective_column].max() < c_star
                )
            else:
                c_star = df_filtered[objective_column].max() - EPS
                df_tol = df_filtered.groupby('stop_val').filter(
                    lambda x: x[objective_column].min() > c_star
                )

            if df_tol.empty:
                text = 'Did not converge'
                times = [df.time.max()]
            else:
                stop_val = df_tol['stop_val'].min()
                this_df = df_filtered[df_filtered['stop_val'] == stop_val]
                text = ''
                times = this_df['time'].tolist()

            plots.append({
                "y": times,
                "text": text,
                "label": solver,
                "color": self.get_style(solver)["color"]
            })

        return plots

    def get_metadata(self, df, dataset, objective, objective_column, minimize):
        return {
            "title": f"{objective}\nData: {dataset}",
            "ylabel": "Time [sec]",
        }


def _get_boxplot_solver(df, objective_column):
    return [
        df.groupby('idx_rep')[['stop_val', objective_column]]
        .apply(lambda x: (
            x[objective_column]
            .loc[x['stop_val'] == x['stop_val'].max()].item()
        )).tolist()
    ]


def _get_boxplot_iteration(df, objective_column):
    return df.groupby('stop_val')[objective_column].apply(
        lambda x: x.tolist()
    ).tolist()


class BoxPlot(BasePlot):
    name = "boxplot"
    type = "boxplot"
    options = {
        "dataset": ...,
        "objective": ...,
        "objective_column": ...,
        "X_axis": ["Solver", "Iteration"],
        "Y_axis": ["Time", "Objective Metric"],
    }

    def plot(self, df, dataset, objective, objective_column, X_axis, Y_axis):
        df = df[df['dataset_name'] == dataset]
        df = df[df['objective_name'] == objective]

        if Y_axis == "Time":
            objective_column = 'time'

        plot_data = []
        for solver, df_filtered in df.groupby('solver_name'):
            if X_axis == "Solver":
                y = _get_boxplot_solver(df_filtered, objective_column)
                x = [solver]
            else:
                y = _get_boxplot_iteration(df_filtered, objective_column)
                x = list(range(len(y)))

            plot_data.append({
                "x": x,
                "y": y,
                "label": solver,
                "color": self.get_style(solver)["color"],
            })

        return plot_data

    def get_metadata(
        self, df, dataset, objective, objective_column, X_axis, Y_axis
    ):
        return {
            "title": f"{objective}\nData: {dataset}",
            "xlabel": X_axis,
            "ylabel": Y_axis,
        }


class TablePlot(BasePlot):
    name = "Table"
    type = "table"
    options = {
        "dataset": ...,
        "objective": ...,
    }

    def plot(self, df, dataset, objective):
        rows = []

        df = df.query(
            'dataset_name == @dataset and objective_name == @objective'
        )
        # Get numeric columns starting with 'objective_'
        objective_cols = [
            col for col in df.select_dtypes(include=['number']).columns
            if col.startswith('objective_')
        ]

        for solver, solver_df in df.groupby('solver_name'):
            solver_res = [solver]
            median_vals = (
               solver_df.groupby('stop_val')
               .median(numeric_only=True).iloc[-1]
            )[objective_cols + ['time']].to_list()

            solver_res.extend(median_vals)
            rows.append(solver_res)

        return rows

    def get_metadata(self, df, dataset, objective):
        df = df.query(
            'dataset_name == @dataset and objective_name == @objective'
        )
        df_filtered = df.select_dtypes(include=['number']).columns
        objective_cols = [
            col.replace('objective_', '') for col in df_filtered
            if col.startswith('objective_')
        ]
        columns = ["solver"] + objective_cols + ["time (s)"]
        return {
            "title": f"{objective}\nData: {dataset}",
            "columns": columns,
        }
