from abc import ABC, abstractmethod
import inspect
import matplotlib.pyplot as plt

from ..utils.dependencies_mixin import DependenciesMixin
from ..utils.parametrized_name_mixin import ParametrizedNameMixin
from ..utils.parametrized_name_mixin import product_param

CMAP = plt.get_cmap('tab20')
COLORS = [CMAP(i) for i in range(CMAP.N)]
COLORS = COLORS[::2] + COLORS[1::2]


class BasePlot(ParametrizedNameMixin, DependenciesMixin, ABC):
    _base_class_name = 'Plot'
    label_dict = {}

    @abstractmethod
    def plot(self, df, **kwargs):
        """Produce plot traces for a given selection.

        Parameters
        ----------
        df : pandas.DataFrame
            Full results dataframe for the run.
        **kwargs :
            Selection parameters that match the plot ``dropdown`` keys
            (e.g. ``dataset``, ``objective``, ``objective_column``).

        Returns
        -------
        list of dict
            List of trace dictionaries. Each trace must include at least
            ``x``, ``y`` and ``label``, ``color``, ``marker``.
            Optional keys: , ``q1``, ``q9``.
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
            Metadata dictionary containing at least ``title``, ``xlabel``
            and ``ylabel``.
        """
        ...

    def get_style(self, label):
        """Get a consistent style dict for a trace label.

        Returns
        -------
        dict
            Contains {'color': color, 'marker': index}
        """

        idx = self.label_dict.get(label, len(self.label_dict))
        self.label_dict[label] = idx

        color = COLORS[idx % len(COLORS)]

        return {'color': color, 'marker': idx}

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
                if k in ["dataset", "solver", "objective"]:
                    dropdown[k] = df[f'{k}_name'].unique().tolist()
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
