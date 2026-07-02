"""Utilities for computing short labels from parametrized class names.

Benchopt class names follow the format::

    ClassName[param1=val1,param2=val2,...]

When many configurations exist but only a few parameters vary across runs,
the full names can be very verbose.  This module provides helpers to produce
*short labels* that only include the parameters that actually differ across
the set of names being compared, together with a tooltip-friendly full label.
"""

from collections import defaultdict

from .parametrized_name_mixin import _extract_options


# ---------------------------------------------------------------------------
# Name parsing
# ---------------------------------------------------------------------------


def parse_parametrized_name(name):
    """Split a parametrized name into its base name and parameter dict.

    Thin wrapper around :func:`_extract_options` kept for backward compat.

    Returns
    -------
    base : str
    params : dict[str, str]  (values converted to str)
    """
    base, _args, kwargs = _extract_options(str(name))
    return base, {k: str(v) for k, v in kwargs.items()}


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

    Parameters
    ----------
    names : sequence of str
        Parametrized names, e.g. from ``df["solver_name"].unique()``.

    Returns
    -------
    short_map : dict[str, str]
        Mapping ``{full_name: short_label}``.  Every element of *names* is
        guaranteed to have an entry.  If short labels are identical to their
        full counterparts (no reduction possible), the dict is still returned
        but ``is_shortened`` will be ``False``.

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
        'OtherSolver[alpha=0.1]':       'OtherSolver[alpha=0.1]',
    }
    """
    names = list(map(str, names))
    # Use _extract_options for robust AST-aware parsing of complex values.
    parsed = {}
    for name in names:
        base, _args, kwargs = _extract_options(name)
        parsed[name] = (base, kwargs)  # kwargs values are Python objects

    # Group by base name
    by_base = defaultdict(list)
    for name, (base, params) in parsed.items():
        by_base[base].append((name, params))

    short_map = {}
    for base, group in by_base.items():
        if len(group) == 1:
            # Single instance – only the base name is needed for identification;
            # showing all params adds noise without aiding disambiguation.
            name, params = group[0]
            short_map[name] = base
            continue

        # Find which parameter keys exist across this group.
        all_keys = []
        seen_keys = set()
        for _, params in group:
            for k in params:
                if k not in seen_keys:
                    all_keys.append(k)
                    seen_keys.add(k)

        # A parameter *varies* if it takes more than one distinct value inside
        # this base-name group (missing values are treated as a distinct value).
        _MISSING = object()
        varying_keys = [
            k for k in all_keys
            if len({str(params.get(k, _MISSING)) for _, params in group}) > 1
        ]

        for name, params in group:
            if not varying_keys:
                # All params are constant – just show the base name.
                short_map[name] = base
            else:
                short_params = {k: str(params[k]) for k in varying_keys if k in params}
                short_map[name] = _format_name(base, short_params)

    return short_map


def is_shortened(short_map):
    """Return True if any label in *short_map* was actually shortened."""
    return any(short != full for full, short in short_map.items())


def compute_params_info(names):
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
