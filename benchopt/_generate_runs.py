import copy
import inspect
import itertools

from .utils.pdb_helpers import exception_handler
from .utils.parametrized_name_mixin import is_matched
from .utils.run_context import RunContext, SeedContextError

# Canonical loop nesting order when no grouping is requested (rep innermost).
CANONICAL_AXES = ('dataset', 'objective', 'solver')
# `repetition` is groupable but needs to be below dataset and objective.
GROUPABLE_AXES = CANONICAL_AXES + ('repetition',)


def _normalize_group_by(group_by):
    """Validate ``group_by`` and return it as a list.

    ``repetition`` must come after ``dataset`` and ``objective``, as the number
    of repetitions (e.g. CV folds) depends on them.
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
        outer = set(group_by[:group_by.index('repetition')])
        if not {'dataset', 'objective'} <= outer:
            raise ValueError(
                "'repetition' in `group_by` must nest inside 'dataset' and "
                "'objective' (both must appear before it), since the fold "
                f"depends on them. Got {group_by}."
            )
    return group_by


def group_runs(run_kwargs_iter, group_by):
    """Yield contiguous batches of run kwargs sharing the ``group_by`` axes.

    Runs must already be ordered by ``group_by`` (see `generate_run_kwargs`).
    Without ``group_by``, each run is its own batch.
    """
    if not group_by:
        yield from ([run_kwargs] for run_kwargs in run_kwargs_iter)
        return
    # `str` as the objective is copied per run; missing axes give 'None'.
    for _, batch in itertools.groupby(
        run_kwargs_iter,
        key=lambda kw: tuple(str(kw.get(axis)) for axis in group_by),
    ):
        yield list(batch)


def _enter_axis(terminal, axis, item, is_installed, i_axis, run_context):
    """Display `item` in the terminal; return False if it is not installed.

    Used by the recursion in `generate_run_kwargs` to skip the subtree of an
    item that is not installed, or of a dataset that skips.
    """
    if axis == 'dataset':
        terminal.set(dataset=item)
        if not is_installed:
            terminal.show_status('not installed', dataset=True)
            return False
        if _skip_before_dispatch(item, terminal, run_context):
            return False
        terminal.display_dataset()
    elif axis == 'objective':
        terminal.set(objective=item)
        if not is_installed:
            terminal.show_status('not installed', objective=True)
            return False
        terminal.display_objective()
    else:  # solver
        terminal.set(solver=item, i_solver=i_axis)
        if not is_installed:
            terminal.show_status('not installed')
            return False
    return True


def _materialize_axes(order, datasets, objectives, solvers):
    """Build each axis's instances, keeping only the outermost one lazy.

    Inner axes are re-entered per outer item, so they are listed and stay in
    memory. Put the heaviest axis (usually ``dataset``) first in ``group_by``.
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


def _run_meta(benchmark, dataset, objective, solver, rep):
    """Build the per-run ``meta`` dict (feeds display and the cache key)."""
    # for plotting purposes consider 'callback' as 'iteration'
    sampling_strategy = solver._solver_strategy
    if sampling_strategy == 'callback':
        sampling_strategy = 'iteration'
    return {
        'base_seed': benchmark.seed,
        'objective_name': str(objective),
        'obj_description': objective.__doc__ or "",
        'solver_name': str(solver),
        'solver_description': inspect.cleandoc(solver.__doc__ or ""),
        'dataset_name': str(dataset),
        'dataset_description': inspect.cleandoc(dataset.__doc__ or ""),
        'idx_rep': rep,
        'sampling_strategy': sampling_strategy.capitalize(),
        'file_objective': objective._module_filename.name,
        **{f"p_obj_{k}": v for k, v in objective._parameters.items()},
        'file_solver': f"solvers/{solver._module_filename.name}",
        **{f"p_solver_{k}": v for k, v in solver._parameters.items()},
        'file_dataset': f"datasets/{dataset._module_filename.name}",
        **{f"p_dataset_{k}": v for k, v in dataset._parameters.items()},
    }


def _skip_before_dispatch(component, terminal, run_context):
    """Display and return whether ``component.skip`` skips its runs.

    A failing `skip` is handled as in a run (traceback, ``--pdb``), displayed
    as an error, and its runs are not created, as for a skip.
    """
    status, reason = 'error', None
    with exception_handler(terminal, pdb=run_context.pdb):
        reason = component._skip_reason()
        status = None if reason is None else 'skip'
    if status is not None:
        level = component._base_class_name
        terminal.skip(
            reason, status=status, dataset=level == 'Dataset',
            objective=level == 'Objective',
        )
    return status is not None


def _prepare_objective(benchmark, run_context, dataset, objective, solver,
                       n_repetitions, terminal):
    """Return the number of repetitions, or ``None`` if the objective skips.

    ``solver`` is None when ``repetition`` is a group_by level, as the fold is
    then shared across solvers.
    """
    run_context.set_run_context(
        objective=objective, dataset=dataset, solver=solver, repetition=0,
        base_seed=benchmark.seed,
    )

    objective._attach_dataset(dataset)
    try:
        # Loads the data only if `skip` needs it.
        skipped = _skip_before_dispatch(objective, terminal, run_context)
        if (not skipped and n_repetitions is None
                and objective._is_using_cv()):
            # The number of repetitions is the number of CV splits.
            objective._load_data()
    except SeedContextError as e:
        if e.component != 'solver':
            raise
        raise ValueError(
            "`group_by` with 'repetition' shares each fold across "
            "solvers, so the data must not depend on the solver -- but "
            "`get_data`/"
            "`set_data` called `get_seed(use_solver=True)`. Remove "
            "'repetition' from `group_by` or make the data "
            "solver-independent."
        ) from e
    if skipped:
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

    The ``group_by`` axes are the outermost loops, so runs sharing them are
    contiguous. ``repetition`` is the innermost axis unless it is in
    ``group_by``.
    """
    group_by = group_by or []
    order = group_by + [a for a in GROUPABLE_AXES if a not in group_by]
    # rep stays the innermost runtime counter unless it is a group_by level.
    rep_is_level = order[-1] != 'repetition'
    axis_items = _materialize_axes(order, datasets, objectives, solvers)
    terminal.set_levels(order if rep_is_level else order[:-1])
    base_ctx = run_context or RunContext()

    def _leaf(chosen):
        """Yield the run kwargs, unless the solver skips this objective."""
        dataset, objective = chosen['dataset'], chosen['objective']
        solver, rep = chosen['solver'], chosen['repetition']
        solver._attach_objective(objective)
        if _skip_before_dispatch(solver, terminal, base_ctx):
            return
        # A shallow copy carries the data if already set (reused in-process),
        # else `_set_dataset` loads it at run time.
        objective_rep = copy.copy(objective)
        # Resolve inheritance now: `meta` feeds the cache key and must not
        # depend on which solver ran first in the process.
        solver._inherit_stopping_criterion(objective)
        meta = _run_meta(benchmark, dataset, objective, solver, rep)
        run_ctx = base_ctx.set_run_context(
            objective=objective_rep, dataset=dataset, solver=solver,
            repetition=rep, base_seed=benchmark.seed,
        )
        yield dict(
            benchmark=benchmark, dataset=dataset, objective=objective_rep,
            solver=solver, repetition=rep, meta=meta, timeout=timeout,
            max_runs=max_runs, terminal=terminal, run_context=run_ctx,
            force=is_matched(str(solver), forced_solvers, default=False),
        )

    def _rec(depth, chosen):
        """Recursively instantiate the product of all components, skipping
        incompatible parts of the tree."""
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
                    yield from _leaf(chosen)
                else:
                    yield from _rec(depth + 1, chosen)
            return
        for i_axis, (item, is_installed) in enumerate(axis_items[axis]):
            if axis == 'dataset':
                # Set for a `skip` loading the data.
                base_ctx.set_run_context(
                    objective=None, dataset=item, solver=None,
                    repetition=None, base_seed=benchmark.seed,
                )
            if not _enter_axis(
                terminal, axis, item, is_installed, i_axis, base_ctx
            ):
                continue
            chosen[axis] = item
            if last:
                yield from _leaf(chosen)
            else:
                yield from _rec(depth + 1, chosen)

    yield from _rec(0, {})
