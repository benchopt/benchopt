"""Short display labels and hover descriptions for parametrized names.

Short labels only keep the parameters that vary across the compared names.
They are display-only and must never be written back into the results.
"""

from html import escape
from collections import defaultdict

from ..utils.parametrized_name_mixin import _extract_options


def _format_name(base, params):
    """Reconstruct a parametrized name from its components."""
    if not params:
        return base
    param_str = ",".join(f"{k}={v}" for k, v in params.items())
    return f"{base}[{param_str}]"


def _format_value(value):
    """Format an integral float as an integer.

    Integer parameters come back as floats from results where their column
    has missing values.
    """
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _default_params(name, base, params):
    """Formatted *params* when *name* is their default name, else None.

    A name formatted with a ``parameter_template`` differs from the default
    one, which lists all the parameters as sorted ``key=value``.
    """
    for fmt in (str, _format_value):
        formatted = {k: fmt(params[k]) for k in sorted(params)}
        if name == _format_name(base, formatted):
            return formatted
    return None


def compute_short_labels(names, params=None):
    """Compute short display labels from a list of parametrized names.

    Short labels include only the parameters that *vary* within a group of
    names sharing the same base class name. Names formatted with a
    ``parameter_template`` are kept as is, as the template already sets the
    label, and so are names whose short label would not be unique.

    Parameters
    ----------
    names : sequence of str
        Parametrized names, e.g. from ``df["solver_name"].unique()``.
    params : dict[str, dict] or None
        Parameters of each name, e.g. from the ``p_solver_*`` columns of the
        results. When None, they are parsed from the names.

    Returns
    -------
    short_map : dict[str, str]
        Mapping ``{full_name: short_label}`` for every name.
    """
    short_map, by_base = {}, defaultdict(list)
    for name in map(str, names):
        base, _, parsed = _extract_options(name)
        formatted = _default_params(
            name, base, parsed if params is None else params[name]
        )
        if formatted is None:
            short_map[name] = name
        else:
            by_base[base].append((name, formatted))

    for base, group in by_base.items():
        # Keep the parameters taking several values across the group.
        values = defaultdict(set)
        for _, formatted in group:
            for k, v in formatted.items():
                values[k].add(v)
        varying = {k for k, vals in values.items() if len(vals) > 1}

        for name, formatted in group:
            short_map[name] = _format_name(base, {
                k: v for k, v in formatted.items() if k in varying
            })

    # A short label shared by several names would merge them in the plots.
    counts = defaultdict(int)
    for short in short_map.values():
        counts[short] += 1
    return {
        name: short if counts[short] == 1 else name
        for name, short in short_map.items()
    }


def _format_description(params, description=""):
    """Render the hover HTML: free-text description and parameters table."""
    parts = []
    if description:
        parts.append(f'<div class="param-desc">{escape(description)}</div>')
    if params:
        rows = "".join(
            f'<tr><td class="param-key">{escape(k)}</td>'
            f'<td class="param-val">{escape(v)}</td></tr>'
            for k, v in params.items()
        )
        parts.append(
            f'<div class="param-title">Parameters</div><table>{rows}</table>'
        )
    return "".join(parts)


def compute_descriptions(names, prose=None, params=None):
    """Compute hover-icon HTML describing each name.

    Parameters
    ----------
    names : sequence of str
        Parametrized names, e.g. ``df["solver_name"].unique()``.
    prose : dict[str, str] or None
        Optional ``{name: free_text}`` (e.g. solver docstrings) prepended to
        the parameters table.
    params : dict[str, dict] or None
        Parameters of each name. When None, they are parsed from the names.

    Returns
    -------
    descriptions : dict[str, str]
        Mapping ``{name: html}``, empty when there is nothing to show.
    """
    prose = prose or {}
    descriptions = {}
    for name in map(str, names):
        name_params = (
            _extract_options(name)[2] if params is None else params[name]
        )
        name_params = {k: _format_value(v) for k, v in name_params.items()}
        descriptions[name] = _format_description(
            name_params, prose.get(name, "")
        )
    return descriptions


# Description column of each name column, in hover priority order.
_DESCRIPTION_COLUMNS = {
    "solver_name": "solver_description",
    "dataset_name": "dataset_description",
    "objective_name": "obj_description",
}
# Prefix of the parameter columns of each name column.
_PARAMS_PREFIX = {
    "solver_name": "p_solver_",
    "dataset_name": "p_dataset_",
    "objective_name": "p_obj_",
}


def _get_params(df, col):
    """Parameters of each name of *col*, from the ``p_*`` columns of *df*.

    Returns None when *df* has no parameter column for *col*.
    """
    prefix = _PARAMS_PREFIX[col]
    p_cols = [c for c in df.columns if c.startswith(prefix)]
    if not p_cols:
        return None
    first = df.groupby(df[col].astype(str))[p_cols].first()
    return {
        # Missing values are None or NaN, for the other names' parameters.
        name: {
            c[len(prefix):]: v for c, v in row.items()
            if not (v is None or (isinstance(v, float) and v != v))
        }
        for name, row in first.iterrows()
    }


def shorten_names(df):
    """Return a copy of *df* with solver/dataset/objective names shortened.

    The full names move to ``*_full_name`` columns, and the description
    columns are replaced by the hover HTML.

    Parameters
    ----------
    df : pandas.DataFrame
        Results dataframe, with ``*_name`` columns holding full names.

    Returns
    -------
    df : pandas.DataFrame
        Copy of *df* with shortened ``*_name`` columns, added ``*_full_name``
        columns and HTML ``*_description`` columns.
    """
    df = df.copy()
    for col, desc_col in _DESCRIPTION_COLUMNS.items():
        if col not in df.columns:
            continue
        names = df[col].astype(str)
        unique = names.unique().tolist()
        params = _get_params(df, col)
        short_map = compute_short_labels(unique, params)

        # Docstring per name, read before the name column is overwritten.
        prose = {}
        if desc_col in df.columns:
            prose = {
                str(k): (v or "")
                for k, v in df.groupby(col)[desc_col].first().items()
            }
        desc = compute_descriptions(unique, prose, params)

        full_col = col.replace("_name", "_full_name")
        df[full_col] = names
        df[col] = names.map(short_map)
        df[desc_col] = names.map(desc)
    return df
