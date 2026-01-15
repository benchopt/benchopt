from abc import ABC, abstractmethod
import inspect
import matplotlib.pyplot as plt

from ..utils.dependencies_mixin import DependenciesMixin
from ..utils.parametrized_name_mixin import ParametrizedNameMixin
from ..utils.parametrized_name_mixin import product_param
from ..utils.parametrized_name_mixin import sanitize

CMAP = plt.get_cmap('tab20')
COLORS = [CMAP(i) for i in range(CMAP.N)]
COLORS = COLORS[::2] + COLORS[1::2]


class BasePlot(ParametrizedNameMixin, DependenciesMixin, ABC):
    _base_class_name = 'Plot'
    _label_dict = {}
    options = {}

    @abstractmethod
    def plot(self, df, **kwargs):
        """Produce plot traces for a given selection.

        Parameters
        ----------
        df : pandas.DataFrame
            Full results dataframe for the run.
        **kwargs :
            Selection parameters that match the plot ``options`` keys
            (e.g. ``dataset``, ``objective``, ``objective_column``).

        Returns
        -------
        The plot data structure, depending on the plot type:
        - scatter: list of dict for each trace, requires: 'x', 'y',
                'label', optional: 'marker', 'color', 'x_low',
                'x_high'.
        - bar_chart: list of dict for each bar, requires: 'y',
                'label', optional: 'color', 'text'.
        - boxplot: list of dict for each box, requires: 'x', 'y',
                'label', optional: 'color'.
        - table: list of list, each inner list is a row of the table.

        Please refer to :ref:`add_custom_plot` for a complete description
        of the plot data.
        """
        ...

    @abstractmethod
    def get_metadata(self, df, **kwargs):
        """Return short metadata for the plot.

        Parameters
        ----------
        df : pandas.DataFrame
            Full results dataframe for the run.
        **kwargs :
            Same selection parameters as for ``plot``.

        Returns
        -------
        dict
            Metadata dictionary.
        """
        ...

    def get_style(self, label):
        """Get a consistent style dict for a trace label.

        Returns
        -------
        dict
            Contains {'color': color, 'marker': index}
        """

        idx = self._label_dict.get(label, len(self._label_dict))
        self._label_dict[label] = idx

        color = COLORS[idx % len(COLORS)]

        return {'color': color, 'marker': idx}

    @classmethod
    def _get_name(cls):
        """Get a simple name for plot comparison"""
        return sanitize(cls.name)

    def _check(self):
        self._check_type()
        self._check_options()

    def _check_type(self):
        if not hasattr(self, 'type'):
            raise ValueError("Plot should have a `type` attribute.")
        supported_types = ['scatter', 'bar_chart', 'boxplot', 'table']
        if self.type not in supported_types:
            raise ValueError(
                f"Plot type should be one of {' '.join(supported_types)}. "
                f"Got {self.type}."
            )

    def _check_options(self):
        if not hasattr(self, 'options'):
            self.options = {}
        if not isinstance(self.options, dict):
            raise ValueError("`options` should be a dictionary.")
        for key, values in self.options.items():
            if values is Ellipsis:
                continue
            if not isinstance(values, list):
                raise ValueError(
                    f"The values of options should be a list or ... . "
                    f"Got {values} for key {key}."
                )

            if len(values) == 0:
                raise ValueError(
                    f"The values of options should be non empty. "
                    f"Got {values} for key {key}."
                )

        keys = set(self.options.keys())
        plot_kwargs = set([
            name for name in inspect.signature(self.plot).parameters
            if name != 'df'
        ])

        # Make sure all options keys are in the plot signature
        if not keys == plot_kwargs:
            raise ValueError(
                f"The keys of options {keys} should match the signature of "
                f"`plot` function, {plot_kwargs}."
            )

    def _get_all_plots(self, df):
        # Get all combinations
        options = {**self.options}
        for k, v in options.items():
            if v is Ellipsis:
                if k in ["dataset", "solver", "objective"]:
                    options[k] = df[f'{k}_name'].unique().tolist()
                elif k == "objective_column":
                    options["objective_column"] = [
                        c for c in df.columns
                        if c.startswith('objective_') and c != 'objective_name'
                    ]
                else:
                    options[k] = df[k].unique().tolist()

        combinations = product_param(options)

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

        return plots, options
