from benchopt import BasePlot


class Plot(BasePlot):
    name = "plot test"
    x_axis = "Custom time"
    y_axis = "Custom objective"

    def plot_data(df):
        return {
            'y': df['objective_value'].tolist(),
            'x': df['time'].tolist(),
        }

    # TODO add possible selection fields
    # faire produit cartésien des selections possibles
