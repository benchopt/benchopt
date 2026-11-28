"""Short display labels and hover descriptions for parametrized names.

Short labels only keep the parameters that vary across the compared names,
and keep the names set by a ``parameter_template`` as is. They are
display-only and must never be written back into the results.
"""

from html import escape
from collections import Counter, defaultdict

from ..utils.parametrized_name_mixin import _extract_options


def _format_name(base, params):
    """Reconstruct a parametrized name from its components."""
    if not params:
        return base
    param_str = ",".join(f"{k}={v}" for k, v in params.items())
    return f"{base}[{param_str}]"


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


def compute_labels(default_names, prose=None):
    """Compute the short display label and hover HTML of each name.

    Short labels include only the parameters that *vary* within a group of
    names sharing the same base class name. A name set by a
    ``parameter_template`` is kept as is, as the template already sets the
    label, and so are names whose short label would not be unique. The hover
    HTML shows the free-text description and all the parameters of a name.

    Parameters
    ----------
    default_names : dict[str, str]
        Mapping ``{name: default_name}`` of the parametrized names, e.g. from
        ``df["solver_name"]``, where the default name ignores the
        ``parameter_template`` and lists all the parameters as ``key=value``
        (e.g. ``df["solver_default_name"]``).
    prose : dict[str, str] or None
        Optional ``{name: free_text}`` (e.g. solver docstrings) prepended to
        the parameters table.

    Returns
    -------
    short_map : dict[str, str]
        Mapping ``{full_name: short_label}`` for every name.
    descriptions : dict[str, str]
        Mapping ``{name: html}``, empty when there is nothing to show.
    """
    prose = prose or {}
    short_map, descriptions, by_base = {}, {}, defaultdict(list)
    for name, default in default_names.items():
        base, args, params = _extract_options(default)
        descriptions[name] = _format_description(
            {k: str(v) for k, v in params.items()}, prose.get(name, "")
        )
        if args or name != _format_name(base, params):
            short_map[name] = name
        else:
            by_base[base].append((name, params))

    for base, group in by_base.items():
        # Keep the parameters taking several values across the group.
        values = defaultdict(set)
        for _, params in group:
            for k, v in params.items():
                values[k].add(str(v))
        varying = {k for k, vals in values.items() if len(vals) > 1}

        for name, params in group:
            short = {k: v for k, v in params.items() if k in varying}
            short_map[name] = _format_name(base, short)

    # A short label shared by several names would merge them in the plots.
    counts = Counter(short_map.values())
    short_map = {
        name: short if counts[short] == 1 else name
        for name, short in short_map.items()
    }
    return short_map, descriptions


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
        columns and HTML ``*_description`` columns. A ``solver_tag`` column
        holds the base name of the solvers that share it with another one,
        and None for the others.
    """
    df = df.copy()
    for col, desc_col in _DESCRIPTION_COLUMNS.items():
        if col not in df.columns:
            continue
        names = df[col].astype(str)
        # The names without parameter_template have the prefix of the
        # description, e.g. `obj_` and not `objective_`, which marks metrics.
        # Results from older benchopt versions have no default names.
        default_col = desc_col.replace("description", "default_name")
        defaults = df.get(default_col, names).astype(str)
        default_names = dict(zip(names, defaults))

        # Docstring per name, read before the name column is overwritten.
        prose = {}
        if desc_col in df.columns:
            prose = {
                str(k): (v or "")
                for k, v in df.groupby(col)[desc_col].first().items()
            }
        short_map, desc = compute_labels(default_names, prose)
        if col == "solver_name":
            bases = {
                n: _extract_options(d)[0] for n, d in default_names.items()
            }
            counts = Counter(bases.values())
            df["solver_tag"] = names.map(
                {n: b if counts[b] > 1 else None for n, b in bases.items()}
            )

        full_col = col.replace("_name", "_full_name")
        df[full_col] = names
        df[col] = names.map(short_map)
        df[desc_col] = names.map(desc)
    return df
