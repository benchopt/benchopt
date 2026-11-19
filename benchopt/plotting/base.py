from abc import ABC, abstractmethod
import inspect
import re
import matplotlib.pyplot as plt

from ..utils.dependencies_mixin import DependenciesMixin
from ..utils.parametrized_name_mixin import ParametrizedNameMixin
from ..utils.parametrized_name_mixin import product_param
from ..utils.parametrized_name_mixin import sanitize
from .short_labels import _DESCRIPTION_COLUMNS

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
                'label', optional: 'marker', 'color', 'x_low', 'x_high',
                'description'.
        - bar_chart: list of dict for each bar, requires: 'y',
                'label', optional: 'color', 'text'.
        - boxplot: list of dict for each box, requires: 'x', 'y',
                'label', optional: 'color'.
        - table: list of list, each inner list is a row of the table. A cell
                can be a ``{'value', 'description'}`` dict.
        - image: list of dict for each image, requires: 'image',
                optional: 'label'.

        Names in ``df`` are short labels. A trace or cell holding a solver,
        dataset or objective name gets its description by default.

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

        color = tuple(COLORS[idx % len(COLORS)])

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
        supported_types = ['scatter', 'bar_chart', 'boxplot', 'table', 'image']
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
            if callable(values):
                continue
            if not isinstance(values, list):
                raise ValueError(
                    f"The values of options should be a list, a callable "
                    f"or ... . Got {values} for key {key}."
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
            if callable(v):
                values = v(df)
                if not isinstance(values, list):
                    raise ValueError(
                        f"The callable for option {k} should return a list. "
                        f"Got {values}."
                    )
                options[k] = values
            elif v is Ellipsis:
                if k in ["dataset", "solver", "objective"]:
                    options[k] = df[f'{k}_name'].unique().tolist()
                elif k == "objective_column":
                    # Skip the name columns added by `shorten_names`.
                    not_metrics = ('objective_name', 'objective_full_name')
                    options["objective_column"] = [
                        c for c in df.columns
                        if c.startswith('objective_') and c not in not_metrics
                    ]
                else:
                    options[k] = df[k].unique().tolist()

        # Hover HTML of each solver/dataset/objective name, solver first on a
        # shared short label. An empty description shows no icon.
        descriptions = {}
        for col, desc_col in _DESCRIPTION_COLUMNS.items():
            if desc_col in df:
                names = df.drop_duplicates(col)[[col, desc_col]].values
                for name, desc in names:
                    descriptions.setdefault(name, desc or None)

        options = {
            k: [_with_description(v, descriptions) for v in values]
            for k, values in options.items()
        }
        combinations = product_param({
            k: [v['value'] for v in values] for k, values in options.items()
        })

        plots = {}
        for kwargs in combinations:
            data = self.get_metadata(df, **kwargs)
            data["type"] = self.type
            data["data"] = self.plot(df, **kwargs)
            if self.type == "scatter":
                for trace in data["data"]:
                    trace.setdefault(
                        "description", descriptions.get(trace["label"])
                    )
            elif self.type == "table":
                data["data"] = [
                    [_describe_cell(c, descriptions) for c in row]
                    for row in data["data"]
                ]
            key_list = (
                [self._get_name()] + list(kwargs.values())
            )
            key = '_'.join(map(str, key_list))
            plots[key] = data

        return plots, options


def _with_description(value, descriptions):
    """Return ``value`` as a ``{'value', 'description'}`` dict.

    An explicit dict is kept as is; a plain value gets its description from
    ``descriptions`` (``None`` if it is not a solver/dataset/objective name).
    """
    if isinstance(value, dict):
        return value
    return {"value": value, "description": descriptions.get(value)}


# Cell markup, as rendered by the HTML report (see `CELL_MARKUP` in result.js).
_CELL_MARKUP = [r"\*\*([^*]+)\*\*", r"__([^_]+)__", r"\*([^*]+)\*"]


def _describe_cell(cell, descriptions):
    """Wrap a string cell naming an object, ignoring its markup."""
    if not isinstance(cell, str):
        return cell
    name = cell
    for pattern in _CELL_MARKUP:
        name = re.sub(pattern, r"\1", name)
    if name not in descriptions:
        return cell
    return {"value": cell, "description": descriptions[name]}
