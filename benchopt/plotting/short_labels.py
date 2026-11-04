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


def compute_short_labels(names):
    """Compute short display labels from a list of parametrized names.

    Short labels include only the parameters that *vary* within a group of
    names sharing the same base class name.

    Parameters
    ----------
    names : sequence of str
        Parametrized names, e.g. from ``df["solver_name"].unique()``.

    Returns
    -------
    short_map : dict[str, str]
        Mapping ``{full_name: short_label}`` for every name.
    """
    by_base = defaultdict(list)
    for name in map(str, names):
        base, _args, params = _extract_options(name)
        by_base[base].append((name, params))

    short_map = {}
    for base, group in by_base.items():
        if len(group) == 1:
            short_map[group[0][0]] = base
            continue

        # Keep the parameters taking several values across the group.
        values = defaultdict(set)
        for _, params in group:
            for k, v in params.items():
                values[k].add(str(v))
        varying = {k for k, vals in values.items() if len(vals) > 1}

        for name, params in group:
            short = {k: v for k, v in params.items() if k in varying}
            short_map[name] = _format_name(base, short)

    return short_map


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


def compute_descriptions(names, prose=None):
    """Compute hover-icon HTML describing each name.

    Parameters
    ----------
    names : sequence of str
        Parametrized names, e.g. ``df["solver_name"].unique()``.
    prose : dict[str, str] or None
        Optional ``{name: free_text}`` (e.g. solver docstrings) prepended to
        the parameters table.

    Returns
    -------
    descriptions : dict[str, str]
        Mapping ``{name: html}``, empty when there is nothing to show.
    """
    prose = prose or {}
    descriptions = {}
    for name in map(str, names):
        _, _, params = _extract_options(name)
        params = {k: str(v) for k, v in params.items()}
        descriptions[name] = _format_description(params, prose.get(name, ""))
    return descriptions


# Description column of each name column, in hover priority order.
_DESCRIPTION_COLUMNS = {
    "solver_name": "solver_description",
    "dataset_name": "dataset_description",
    "objective_name": "obj_description",
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
        short_map = compute_short_labels(unique)

        # Docstring per name, read before the name column is overwritten.
        prose = {}
        if desc_col in df.columns:
            prose = {
                str(k): (v or "")
                for k, v in df.groupby(col)[desc_col].first().items()
            }
        desc = compute_descriptions(unique, prose)

        full_col = col.replace("_name", "_full_name")
        df[full_col] = names
        df[col] = names.map(short_map)
        df[desc_col] = names.map(desc)
    return df
