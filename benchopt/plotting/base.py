from abc import ABC, abstractmethod
import inspect
import matplotlib.pyplot as plt

from ..utils.dependencies_mixin import DependenciesMixin
from ..utils.parametrized_name_mixin import ParametrizedNameMixin
from ..utils.parametrized_name_mixin import product_param
from ..utils.parametrized_name_mixin import sanitize
from ..utils.short_labels import (
    compute_short_labels, compute_params_info, format_description
)

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
                'x_high', 'short_label', 'description'. ``description`` text
                shows on a legend hover icon when short labels are toggled
                on (a parametrized name renders as its params table).
        - bar_chart: list of dict for each bar, requires: 'y',
                'label', optional: 'color', 'text', 'short_label'.
        - boxplot: list of dict for each box, requires: 'x', 'y',
                'label', optional: 'color', 'short_label'.
        - table: list of list, each inner list is a row of the table.
                The first column can be shortened via the optional
                'short_labels' / 'descriptions' metadata keys (see
                ``get_metadata``).
        - image: list of dict for each image, requires: 'image',
                optional: 'label'.

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

    def get_default_short_labels(self, labels):
        """Return the default short labels and hover descriptions for *labels*.

        Short labels keep only the parameters that vary across *labels*;
        parameters that are constant are dropped, so the whole set is needed as
        context. The description is the hover-icon HTML: a parameters table
        parsed from the label, injected into the legend tooltip as-is (so it
        must be valid HTML), empty when the label has no parameters. This is
        the default scheme: a plot calls it from :meth:`plot` and sets
        ``short_label`` / ``description`` on its traces, which leaves it free
        to decide what each trace displays.

        Parameters
        ----------
        labels : sequence of str
            All trace labels, e.g. ``[t["label"] for t in traces]``.

        Returns
        -------
        dict[str, dict]
            Mapping ``{label: {"short_label": str, "description": str}}``;
            every input label has an entry.
        """
        short_labels = compute_short_labels(labels)
        params_info = compute_params_info(labels)
        return {
            label: {
                "short_label": short_labels[label],
                "description": format_description(
                    params_info.get(str(label), {})
                ),
            }
            for label in labels
        }

    def _annotate_short_labels(self, traces):
        """Add ``full_label``/``short_label``/``description`` to each trace."""
        annotations = self.get_default_short_labels(
            [t["label"] for t in traces]
        )
        for t in traces:
            t["full_label"] = t["label"]
            t.update(annotations[t["label"]])
