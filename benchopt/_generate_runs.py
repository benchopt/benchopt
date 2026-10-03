import copy
import inspect
import itertools

from .utils.parametrized_name_mixin import is_matched
from .utils.run_context import RunContext, SeedContextError

# Canonical loop nesting order when no grouping is requested (rep innermost).
CANONICAL_AXES = ('dataset', 'objective', 'solver')
# `repetition` is groupable but needs the generator hoist to nest above solver.
GROUPABLE_AXES = CANONICAL_AXES + ('repetition',)


def _normalize_group_by(group_by):
    """Validate ``group_by`` and return it as a list.

    ``repetition`` is a valid axis, but its cardinality is resolved per
    (dataset, objective) (possibly from ``objective.cv``, where each rep is a
    different fold), so it must nest *inside* ``dataset`` and ``objective`` --
    i.e. both must also be in ``group_by``. It is otherwise free relative to
    ``solver``: ``[dataset, objective, repetition]`` batches solvers under a
    fold (sharing per-fold setup); ``[dataset, objective, solver]`` batches
    reps under a config (sharing solver state).
    """
    if not group_by:
        return []
    if isinstance(group_by, str):
        group_by = [group_by]
    group_by = list(group_by)
    unknown = [a for a in group_by if a not in GROUPABLE_AXES]
    if unknown:
        raise ValueError(
            f"Unknown `group_by` axes {unknown}. Valid axes: {GROUPABLE_AXES}."
        )
    if len(set(group_by)) != len(group_by):
        raise ValueError(f"Duplicate axes in `group_by`: {group_by}.")
    if 'repetition' in group_by:
        # 'dataset' and 'objective' must not only be present but nest *outside*
        # rep (the fold depends on them), i.e. appear before it in the order.
        outer = set(group_by[:group_by.index('repetition')])
        if not {'dataset', 'objective'} <= outer:
            raise ValueError(
                "'repetition' in `group_by` must nest inside 'dataset' and "
                "'objective' (both must appear before it), since the fold "
                f"depends on them. Got {group_by}."
            )
    return group_by


def _ordered_axes(group_by):
    """Loop nesting order with the ``group_by`` axes outermost.

    ``group_by=None`` keeps the canonical ``dataset -> objective -> solver``
    order, so the default run stream is unchanged. A str or list of axes moves
    those axes to the front (outermost), making runs contiguous by that key.

    The order also drives memory: only the outermost axis is streamed (see
    :func:`_materialize_axes`), so list the heaviest, data-carrying axis first.
    """
    group_by = _normalize_group_by(group_by)
    # Remaining axes keep canonical order; rep stays innermost by default.
    rest = [a for a in GROUPABLE_AXES if a not in group_by]
    return group_by + rest


# `prepare` kwargs carry no `meta`, hence `.get('meta', {})` + fallback.
_AXIS_KEY = {
    'dataset': lambda kw: kw.get('meta', {}).get('dataset_name',
                                                 kw.get('dataset')),
    'objective': lambda kw: kw.get('meta', {}).get('objective_name',
                                                   kw.get('objective')),
    'solver': lambda kw: kw.get('meta', {}).get('solver_name',
                                                kw.get('solver')),
    'repetition': lambda kw: kw.get('meta', {}).get('idx_rep'),
}


def group_runs(run_kwargs_iter, group_by):
    """Yield contiguous batches of run kwargs sharing the ``group_by`` key.

    Relies on the generator emitting runs already ordered by ``group_by`` (see
    :func:`_ordered_axes`), so grouping is a lazy ``itertools.groupby`` with no
    full materialization. ``group_by=None`` yields one run per batch, i.e. the
    default one job per (dataset, objective, solver, repetition). Any config
    grouping collapses that config's repetitions into a single batch (the #860
    goal), since repetitions are always the innermost axis.
    """
    group_by = _normalize_group_by(group_by)
    if not group_by:
        for run_kwargs in run_kwargs_iter:
            yield [run_kwargs]
        return
    keys = [_AXIS_KEY[axis] for axis in group_by]

    def _key(run_kwargs):
        return tuple(k(run_kwargs) for k in keys)

    for _, batch in itertools.groupby(run_kwargs_iter, key=_key):
        yield list(batch)


def _enter_axis(terminal, axis, item, is_installed, i_solver=None):
    """Run terminal side-effects for entering `item`; return False to skip.

    ``i_solver`` is the solver's position in its axis loop; its only use is
    gating ``terminal.skip`` so an objective-skip prints once per (dataset,
    objective) -- so it is passed only for the solver axis.
    """
    if axis == 'dataset':
        terminal.set(dataset=item)
        if not is_installed:
            terminal.show_status('not installed', dataset=True)
            return False
        terminal.display_dataset()
    elif axis == 'objective':
        terminal.set(objective=item)
        if not is_installed:
            terminal.show_status('not installed', objective=True)
            return False
        terminal.display_objective()
    else:  # solver
        terminal.set(solver=item, i_solver=i_solver)
        if not is_installed:
            terminal.show_status('not installed')
            return False
    return True


def _materialize_axes(order, datasets, objectives, solvers):
    """Build each axis's instances, keeping only the outermost lazy.

    The outermost axis (``order[0]``) is iterated once, so it is left as a lazy
    generator -- as in the ungrouped default on ``main``: its instances, and
    the data they cache (e.g. ``Dataset._data``), are freed as the nest
    advances instead of all being held resident. The inner axes are re-entered
    per outer combination, so they are materialized (listed) and stay resident
    for the whole run.

    Ordering therefore matters for memory: only the *outermost* axis is
    streamed. Put the heaviest, data-carrying axis (usually ``dataset``) first
    in ``group_by`` so its data is freed as the run advances -- a heavy axis
    placed after the first group_by axis keeps every one of its instances (and
    their cached data) resident. E.g. ``group_by=['dataset', 'objective']``
    streams datasets, whereas ``['objective', 'dataset']`` holds them all.
    """
    from .benchmark import _list_parametrized_classes
    gens = {
        'dataset': _list_parametrized_classes(*datasets),
        'objective': _list_parametrized_classes(*objectives,
                                                check_installed=False),
        'solver': _list_parametrized_classes(*solvers),
    }
    return {axis: (g if axis == order[0] else list(g))
            for axis, g in gens.items()}


def _run_meta(benchmark, dataset, objective, solver, rep, sampling_strategy,
              obj_description):
    """Build the per-run ``meta`` dict (feeds display and the cache key)."""
    return {
        'base_seed': benchmark.seed,
        'objective_name': str(objective),
        'obj_description': obj_description,
        'solver_name': str(solver),
        'solver_description': inspect.cleandoc(solver.__doc__ or ""),
        'dataset_name': str(dataset),
        'idx_rep': rep,
        'sampling_strategy': sampling_strategy.capitalize(),
        'file_objective': objective._module_filename.name,
        **{f"p_obj_{k}": v for k, v in objective._parameters.items()},
        'file_solver': f"solvers/{solver._module_filename.name}",
        **{f"p_solver_{k}": v for k, v in solver._parameters.items()},
        'file_dataset': f"datasets/{dataset._module_filename.name}",
        **{f"p_dataset_{k}": v for k, v in dataset._parameters.items()},
    }


def _prepare_objective(benchmark, run_context, dataset, objective, solver,
                       n_repetitions, terminal):
    """Set the objective's data and resolve its repetition count.

    Called with the run's ``solver`` on the default (rep-innermost) path, where
    each run reseeds with its own solver. When ``repetition`` is a group_by
    level the fold is shared across solvers, so it is called with
    ``solver=None``: the data must then be solver-independent, and a
    ``get_seed(use_solver=True)`` in ``get_data``/``set_data`` fails fast here
    with a clear error. Returns the repetition count, or ``None`` if skipped.
    """
    run_context.set_run_context(
        objective=objective, dataset=dataset, solver=solver, repetition=0,
        base_seed=benchmark.seed,
    )
    try:
        skip, reason = objective._set_dataset(dataset)
    except SeedContextError as e:
        if e.component != 'solver':
            raise
        raise ValueError(
            "`group_by` with 'repetition' shares each fold across solvers, so "
            "the data must not depend on the solver -- but `get_data`/"
            "`set_data` called `get_seed(use_solver=True)`. Remove "
            "'repetition' from `group_by` or make the data solver-independent."
        ) from e
    if skip:
        terminal.skip(reason, objective=True)
        return None

    if n_repetitions is None:
        if hasattr(objective, "cv"):
            n_repetitions = objective.cv.get_n_splits(
                **getattr(objective, "cv_metadata", {})
            )
        else:
            # 1 by default so the solver runs at least once.
            n_repetitions = 1
    terminal.n_repetitions = n_repetitions
    return n_repetitions


def generate_run_kwargs(
    benchmark, solvers=None, forced_solvers=None, datasets=None,
    objectives=None, n_repetitions=1, max_runs=10, timeout=None,
    collect=False, terminal=None, run_context=None, group_by=None,
):
    """Yield kwargs for each ``run_one_to_cvg`` call in the benchmark.

    Walks the axes in ``group_by`` order (see :func:`_ordered_axes`) as one
    recursive nest, holding the group_by axes constant outermost.
    ``repetition`` is the innermost axis by default -- expanded per
    (dataset, objective, solver) and shown as the ``(k / total)`` counter --
    but becomes a display level (a ``|--rep k`` node) when it is a group_by
    axis, so solvers batch under a shared fold.
    """
    order = _ordered_axes(group_by)
    # rep stays the innermost runtime counter unless it is a group_by level.
    rep_is_level = order[-1] != 'repetition'
    axis_items = _materialize_axes(order, datasets, objectives, solvers)
    terminal.set_levels(order if rep_is_level else order[:-1])
    base_ctx = run_context or RunContext()

    def _leaf(chosen):
        dataset, objective = chosen['dataset'], chosen['objective']
        solver, rep = chosen['solver'], chosen['repetition']
        # A shallow copy carries the already-set data (reused in-process,
        # reloaded on a worker via `_set_dataset`).
        objective_rep = copy.copy(objective)
        # Resolve inheritance now: `meta` feeds the cache key and must not
        # depend on which solver ran first in the process.
        solver._inherit_stopping_criterion(objective)
        # for plotting purposes consider 'callback' as 'iteration'
        sampling_strategy = solver._solver_strategy
        if sampling_strategy == 'callback':
            sampling_strategy = 'iteration'
        meta = _run_meta(benchmark, dataset, objective, solver, rep,
                         sampling_strategy, objective.__doc__ or "")
        run_ctx = base_ctx.set_run_context(
            objective=objective_rep, dataset=dataset, solver=solver,
            repetition=rep, base_seed=benchmark.seed,
        )
        return dict(
            benchmark=benchmark, dataset=dataset, objective=objective_rep,
            solver=solver, repetition=rep, meta=meta, timeout=timeout,
            max_runs=max_runs, terminal=terminal, run_context=run_ctx,
            force=is_matched(str(solver), forced_solvers, default=False),
        )

    def _rec(depth, chosen):
        axis = order[depth]
        last = depth + 1 == len(order)
        if axis == 'repetition':
            n_reps = _prepare_objective(
                benchmark, base_ctx, chosen['dataset'], chosen['objective'],
                chosen.get('solver'), n_repetitions, terminal,
            )
            if n_reps is None:  # skipped (dataset, objective)
                return
            for rep in range(n_reps):
                if rep_is_level:
                    terminal.display_rep(rep)
                chosen['repetition'] = rep
                if last:
                    yield _leaf(chosen)
                else:
                    yield from _rec(depth + 1, chosen)
            return
        for i_axis, (item, is_installed) in enumerate(axis_items[axis]):
            if not _enter_axis(terminal, axis, item, is_installed,
                               i_solver=i_axis):
                continue
            chosen[axis] = item
            if last:
                yield _leaf(chosen)
            else:
                yield from _rec(depth + 1, chosen)

    yield from _rec(0, {})
