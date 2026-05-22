"""Utilities for computing short labels from parametrized class names.

Benchopt class names follow the format::

    ClassName[param1=val1,param2=val2,...]

When many configurations exist but only a few parameters vary across runs,
the full names can be very verbose.  This module provides helpers to produce
*short labels* that only include the parameters that actually differ across
the set of names being compared, together with a tooltip-friendly full label.

The feature can be disabled per-benchmark by setting ``short_labels: false``
in the benchmark's ``benchopt.yml`` configuration file.
"""
import re
from collections import defaultdict


# ---------------------------------------------------------------------------
# Name parsing
# ---------------------------------------------------------------------------

_PARAM_RE = re.compile(r'^(.+?)\[(.+)\]$', re.DOTALL)


def parse_parametrized_name(name):
    """Split a parametrized name into its base name and parameter dict.

    Parameters
    ----------
    name : str
        A name of the form ``"BaseName[p1=v1,p2=v2]"`` or simply
        ``"BaseName"`` (no parameters).

    Returns
    -------
    base : str
        The class name without parameters.
    params : dict[str, str]
        Ordered mapping of parameter name → string value.
        Empty dict when the name has no ``[…]`` suffix.

    Examples
    --------
    >>> parse_parametrized_name("LASSO[alpha=0.1,n_iter=100]")
    ('LASSO', {'alpha': '0.1', 'n_iter': '100'})
    >>> parse_parametrized_name("LASSO")
    ('LASSO', {})
    """
    m = _PARAM_RE.match(name)
    if m is None:
        return name, {}
    base = m.group(1)
    params_str = m.group(2)
    params = {}
    for token in params_str.split(','):
        if '=' in token:
            k, v = token.split('=', 1)
            params[k.strip()] = v.strip()
        else:
            # Malformed token – store as-is under an empty key to avoid loss.
            params[token.strip()] = ''
    return base, params


def _format_name(base, params):
    """Reconstruct a parametrized name from its components."""
    if not params:
        return base
    param_str = ','.join(f'{k}={v}' for k, v in params.items())
    return f'{base}[{param_str}]'


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
    names = list(names)
    parsed = {name: parse_parametrized_name(name) for name in names}

    # Group by base name
    by_base = defaultdict(list)
    for name, (base, params) in parsed.items():
        by_base[base].append((name, params))

    short_map = {}
    for base, group in by_base.items():
        if len(group) == 1:
            # Single instance – keep the full name to preserve context.
            name, _ = group[0]
            short_map[name] = name
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
            if len({params.get(k, _MISSING) for _, params in group}) > 1
        ]

        for name, params in group:
            if not varying_keys:
                # All params are constant – just show the base name.
                short_map[name] = base
            else:
                short_params = {
                    k: params[k] for k in varying_keys if k in params
                }
                short_map[name] = _format_name(base, short_params)

    return short_map


def is_shortened(short_map):
    """Return True if any label in *short_map* was actually shortened."""
    return any(short != full for full, short in short_map.items())


# ---------------------------------------------------------------------------
# Annotate plot data with short / full labels
# ---------------------------------------------------------------------------

def add_short_labels(plot_data, solver_short_map):
    """Annotate a plot-data dict in-place with ``short_label`` / ``full_label``.

    Each curve trace dict is expected to have a ``"label"`` key that holds the
    full solver name.  Two extra keys are added:

    * ``"full_label"`` – identical to the original ``"label"``.
    * ``"short_label"`` – the shortened form from *solver_short_map* (falls
      back to ``"label"`` when the name is not in the map).

    Parameters
    ----------
    plot_data : dict
        The nested ``{plot_name: {key: {data: [{label: …}, …]}}}`` structure
        produced by :meth:`benchopt.Benchmark.get_plot_data`.
    solver_short_map : dict[str, str]
        Mapping returned by :func:`compute_short_labels` for solver names.

    Returns
    -------
    plot_data : dict
        The same object, mutated in-place and returned for convenience.
    """
    for plot_name, plot_keys in plot_data.items():
        for key, plot_entry in plot_keys.items():
            for trace in plot_entry.get('data', []):
                full = trace.get('label')
                if full is not None:
                    trace['full_label'] = full
                    trace['short_label'] = solver_short_map.get(full, full)
    return plot_data
