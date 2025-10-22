from abc import ABC, abstractmethod
import inspect
import matplotlib.pyplot as plt

from ..utils.dependencies_mixin import DependenciesMixin
from ..utils.parametrized_name_mixin import ParametrizedNameMixin
from ..utils.parametrized_name_mixin import product_param

CMAP = plt.get_cmap('tab20')
COLORS = [CMAP(i) for i in range(CMAP.N)]
COLORS = COLORS[::2] + COLORS[1::2]
MARKERS = {i: v for i, v in enumerate(plt.Line2D.markers)}


class BasePlot(ParametrizedNameMixin, DependenciesMixin, ABC):
    _base_class_name = 'Plot'
    label_dict = {}

    @abstractmethod
    def plot(self, df, **kwargs):
        ...

    @abstractmethod
    def get_metadata(self, df, **kwargs):
        ...

    def get_style(self, label, plotly=True):
        idx = self.label_dict.get(label, len(self.label_dict))
        self.label_dict[label] = idx

        color = COLORS[idx % len(COLORS)]

        if plotly:
            color = tuple(
                int(255*x) if i != 3 else float(x)
                for i, x in enumerate(color)
            )
            color = f'rgba{color}'
            marker = idx
        else:
            marker = MARKERS[idx % len(MARKERS)]

        return color, marker

    def _get_name(self):
        return self.name.replace(" ", "_")

    def _check(self):
        self._check_type()
        self._check_dropdown()

    def _check_type(self):
        if not hasattr(self, 'type'):
            raise ValueError("Plot should have a `type` attribute.")
        supported_types = ['scatter']
        if self.type not in supported_types:
            raise ValueError(
                f"Plot type should be one of {' '.join(supported_types)}. "
                f"Got {self.type}."
            )

    def _check_dropdown(self):
        if not hasattr(self, 'dropdown'):
            self.dropdown = {}
        if not isinstance(self.dropdown, dict):
            raise ValueError("`dropdown` should be a dictionary.")
        for key, values in self.dropdown.items():
            if values is Ellipsis:
                continue
            if not isinstance(values, list):
                raise ValueError(
                    f"The values of dropdown should be a list or ... . "
                    f"Got {values} for key {key}."
                )

            if len(values) == 0:
                raise ValueError(
                    f"The values of dropdown should be non empty. "
                    f"Got {values} for key {key}."
                )

        keys = set(self.dropdown.keys())
        plot_kwargs = set([
            name for name in inspect.signature(self.plot).parameters
            if name != 'df'
        ])

        # Make sure all dropdown keys are in the plot signature
        if not keys == plot_kwargs:
            raise ValueError(
                f"The keys of dropdown {keys} should match the signature of "
                f"`plot` function, {plot_kwargs}."
            )

    def _get_all_plots(self, df):
        # Get all combinations
        dropdown = {**self.dropdown}
        for k, v in dropdown.items():
            if v is Ellipsis:
                if k == "dataset":
                    dropdown[k] = df['data_name'].unique().tolist()
                elif k == "solver":
                    dropdown[k] = df['solver_name'].unique().tolist()
                elif k == "objective":
                    dropdown[k] = df['objective_name'].unique().tolist()
                elif k == "objective_column":
                    dropdown["objective_column"] = [
                        c for c in df.columns
                        if c.startswith('objective_') and c != 'objective_name'
                    ]
                else:
                    dropdown[k] = df[k].unique().tolist()

        combinations = product_param(dropdown)

        plots = {}
        for kwargs in combinations:
            data = self.get_metadata(df, **kwargs)
            data["type"] = self.type
            data["data"] = self.plot(df, **kwargs)
            key_list = (
                [self._get_name()] + list(kwargs.values())
            )
            key = '_'.join(map(str, key_list))
            plots[key] = data

        return plots, dropdown

    def _get_plt_plot(self, df, output_dir):
        if self.type == "scatter":
            return self._get_plt_plot_scatter(df, output_dir)
        else:
            raise NotImplementedError(
                f"Plot type {self.type} not implemented for matplotlib."
            )

    def _get_plt_plot_scatter(self, df, output_dir):
        df = df.copy()
        data, _ = self._get_all_plots(df)
        figs = []
        for key, plot_datas in data.items():

            fig = plt.figure()
            for plot_data in plot_datas["data"]:
                color, marker = self.get_style(
                    plot_data["label"], plotly=False
                )
                plt.loglog(
                    plot_data["x"], plot_data["y"], color=color,
                    marker=marker, label=plot_data["label"],
                    linewidth=3
                )

                if "q1" in plot_data and "q9" in plot_data:
                    q1 = plot_data["q1"]
                    q9 = plot_data["q9"]
                    plt.fill_betweenx(
                        plot_data["y"], q1, q9, color=plot_data["color"],
                        alpha=.3
                    )

            # Format the plot to be nice
            plt.legend(fontsize=14)
            plt.xlabel(plot_datas["xlabel"], fontsize=14)
            plt.ylabel(plot_datas["ylabel"], fontsize=14)
            plt.title(plot_datas["title"], fontsize=14)
            plt.tight_layout()

            save_name = output_dir / f"{key}"
            if hasattr(fig, 'write_html'):
                save_name = save_name.with_suffix('.html')
                fig.write_html(str(save_name), include_mathjax='cdn')
            else:
                save_name = save_name.with_suffix('.pdf')
                plt.savefig(save_name)
            print(f'Save {key} as: {save_name}')
            figs.append(fig)

        return figs
