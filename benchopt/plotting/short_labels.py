"""Utilities for computing short labels from parametrized class names.

Benchopt class names follow the format::

    ClassName[param1=val1,param2=val2,...]

When many configurations exist but only a few parameters vary across runs,
the full names can be very verbose.  This module provides helpers to produce
*short labels* that only include the parameters that actually differ across
the set of names being compared, together with a tooltip-friendly full label.

Short labels are **display-only**: they are computed relative to the current
set of names being compared, so they are not stable identifiers and must never
be written back into the results (parquet, published reports, ``*_name``
columns). Use them for plot labels, selectors and tooltips only; keep the full
parametrized name as the canonical identity everywhere data is persisted.
"""

from html import escape
from collections import defaultdict

from ..utils.parametrized_name_mixin import _extract_options


# ---------------------------------------------------------------------------
# Name parsing
# ---------------------------------------------------------------------------


def _format_name(base, params):
    """Reconstruct a parametrized name from its components."""
    if not params:
        return base
    param_str = ",".join(f"{k}={v}" for k, v in params.items())
    return f"{base}[{param_str}]"


# ---------------------------------------------------------------------------
# Short label computation
# ---------------------------------------------------------------------------


def compute_short_labels(names):
    """Compute short display labels from a list of parametrized names.

    Short labels include only the parameters that *vary* within a group of
    names sharing the same base class name.  Parameters that are constant
    across all instances of a class are dropped from the label.

    When a class appears only once in *names* the full name is kept so that
    relevant context is not lost.

    The returned labels are display-only and relative to *names*; do not use
    them as stable identifiers or write them back into persisted results (see
    the module docstring).

    Parameters
    ----------
    names : sequence of str
        Parametrized names, e.g. from ``df["solver_name"].unique()``.

    Returns
    -------
    short_map : dict[str, str]
        Mapping ``{full_name: short_label}``.  Every element of *names* is
        guaranteed to have an entry (identical to the full name when no
        reduction is possible).

    Examples
    --------
    >>> names = [
    ...     "Solver[alpha=0.1,n_iter=100]",
    ...     "Solver[alpha=0.5,n_iter=100]",
    ...     "OtherSolver[alpha=0.1]",
    ... ]
    >>> compute_short_labels(names)
    {
        'Solver[alpha=0.1,n_iter=100]': 'Solver[alpha=0.1]',
        'Solver[alpha=0.5,n_iter=100]': 'Solver[alpha=0.5]',
        'OtherSolver[alpha=0.1]':       'OtherSolver',
    }
    """
    # Parse each name into (base, params); `_extract_options` is AST-aware so
    # complex values (lists, dicts, tuples) are handled. Names come from a
    # parameters dict, so they carry only keyword params (no positional args).
    by_base = defaultdict(list)
    for name in map(str, names):
        base, _args, params = _extract_options(name)
        by_base[base].append((name, params))

    short_map = {}
    for base, group in by_base.items():
        if len(group) == 1:
            # Single instance: the base name alone identifies it.
            short_map[group[0][0]] = base
            continue

        # All names of a class share the same parameters, so keep exactly the
        # ones that take more than one distinct value across the group.
        values = defaultdict(set)
        for _, params in group:
            for k, v in params.items():
                values[k].add(str(v))
        varying = {k for k, vals in values.items() if len(vals) > 1}

        for name, params in group:
            short = {k: v for k, v in params.items() if k in varying}
            short_map[name] = _format_name(base, short)

    return short_map


def _compute_params_info(names):
    """Return ``{full_name: {param: str_value}}`` parsed from *names*.

    Uses :func:`_extract_options` for robust AST-aware parsing so that
    complex values (lists, dicts, tuples) are handled correctly.

    Parameters
    ----------
    names : sequence of str

    Returns
    -------
    params_info : dict[str, dict[str, str]]
    """
    result = {}
    for name in names:
        name_str = str(name)
        base, _args, kwargs = _extract_options(name_str)
        result[name_str] = {k: str(v) for k, v in kwargs.items()}
    return result


def _format_description(params, description=""):
    """Render an object's hover-icon HTML (empty when there is nothing to show).

    Combines an optional free-text ``description`` (e.g. a solver docstring)
    with a table of the object's ``{param: value}`` parameters.
    """
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
        Mapping ``{name: html}``; the HTML combines the free-text description
        and a small parameters table (empty string when there is neither).
        Useful for a custom plot that needs the same hover tooltip as the
        default plots.
    """
    prose = prose or {}
    return {
        name: _format_description(params, prose.get(name, ""))
        for name, params in _compute_params_info(names).items()
    }


# Free-text description columns associated with each name column, when present.
_DESCRIPTION_COLUMNS = {
    "solver_name": "solver_description",
    "dataset_name": "dataset_description",
    "objective_name": "obj_description",
}


def shorten_names(
    df, columns=("solver_name", "dataset_name", "objective_name")
):
    """Return a copy of *df* with entity name columns shortened for display.

    For each column in *columns* present in *df*, the original full names are
    preserved in a companion ``*_full_name`` column (opt-in for custom plots
    that need the full parametrized name), and the column itself is replaced by
    its short label. The ``{short_label: description_html}`` map for the hover
    tooltips is returned alongside, combining any free-text description column
    (e.g. ``solver_description``) with the object's parameters table.

    Short labels are display-only (see the module docstring): this operates on
    a copy and must only be used on the plotting ``df``, never on the results
    that get persisted.

    Parameters
    ----------
    df : pandas.DataFrame
        Results dataframe, with ``*_name`` columns holding full names.
    columns : sequence of str
        Name columns to shorten when present.

    Returns
    -------
    df : pandas.DataFrame
        Copy of *df* with shortened ``*_name`` columns and added
        ``*_full_name`` columns.
    descriptions : dict[str, str]
        Mapping ``{short_label: description_html}`` for every shortened name.
    """
    df = df.copy()
    descriptions = {}
    for col in columns:
        if col not in df.columns:
            continue
        names = df[col].astype(str)
        unique = names.unique().tolist()
        short_map = compute_short_labels(unique)

        # Pull the free-text description (docstring) per name, if the benchmark
        # recorded one, before the name column is overwritten.
        desc_col = _DESCRIPTION_COLUMNS.get(col)
        prose = {}
        if desc_col and desc_col in df.columns:
            prose = {
                str(k): (v or "")
                for k, v in df.groupby(col)[desc_col].first().items()
            }
        desc = compute_descriptions(unique, prose)

        full_col = col.replace("_name", "_full_name")
        df[full_col] = names
        df[col] = names.map(short_map)
        descriptions.update(
            {short_map[name]: desc[name] for name in unique}
        )
    return df, descriptions
