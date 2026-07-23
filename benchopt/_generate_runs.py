import copy
import inspect

from .utils.parametrized_name_mixin import is_matched
from .utils.run_context import RunContext


def buffer_iterator(it):
    """Buffer the output of an iterator to repeat it without recomputing."""
    buffer = []

    def buffered_it(buffer):
        for val in it:
            buffer.append(val)
            yield val

    return buffered_it(buffer), buffer


def _get_all_runs(benchmark, solvers=None, forced_solvers=None,
                  datasets=None, objectives=None, terminal=None):
    """Generator with all combinations to run for the benchmark.

    Parameters
    ----------
    benchmark : benchopt.Benchmark object
        Object to represent the benchmark.
    solvers : list | None
        List of solvers to include in the benchmark. If None
        all solvers available are run.
    forced_solvers : list | None
        List of solvers to include in the benchmark and for
        which one forces recomputation.
    datasets : list | None
        List of datasets to include. If None all available
        datasets are used.
    objectives : list | None
        Filters to select specific objective parameters. If None,
        all objective parameters are tested
    terminal : TerminalOutput or None
        Object to format string to display the terminal.

    Yields
    ------
    dataset : BaseDataset instance
    objective : BaseObjective instance
    solver : BaseSolver instance
    force : bool
    """
    from .benchmark import _list_parametrized_classes

    all_datasets = _list_parametrized_classes(*datasets)
    all_solvers, solvers_buffer = buffer_iterator(
        _list_parametrized_classes(*solvers)
    )
    for dataset, is_installed in all_datasets:
        terminal.set(dataset=dataset)
        if not is_installed:
            terminal.show_status('not installed', dataset=True)
            continue
        terminal.display_dataset()
        all_objectives = _list_parametrized_classes(
            *objectives, check_installed=False
        )
        for objective, is_installed in all_objectives:
            terminal.set(objective=objective)
            if not is_installed:
                terminal.show_status('not installed', objective=True)
                continue
            terminal.display_objective()
            for i_solver, (solver, is_installed) in enumerate(all_solvers):
                terminal.set(solver=solver, i_solver=i_solver)

                if not is_installed:
                    terminal.show_status('not installed')
                    continue

                force = is_matched(
                    str(solver), forced_solvers, default=False
                )
                yield dict(
                    dataset=dataset, objective=objective, solver=solver,
                    force=force, terminal=terminal
                )
            all_solvers = solvers_buffer


def get_solver_kwargs(
    benchmark, dataset, objective, solver, n_repetitions, max_runs,
    timeout=None, force=False, collect=False, terminal=None,
    run_context=None,
):
    """Run a benchmark for a given dataset, objective and solver.

    Parameters
    ----------
    benchmark : benchopt.Benchmark object
        Object to represent the benchmark.
    dataset : instance of BaseDataset
        The dataset used for this benchmark.
    objective : instance of BaseObjective
        The objective to minimize.
    solver : instance of BaseSolver
        The solver to use.
    n_repetitions : int
        The number of repetitions to run. Defaults to 1.
    max_runs : int
        The maximum number of solver runs to perform to estimate
        the convergence curve.
    timeout : float
        The maximum duration in seconds of the solver run.
    force : bool
        If force is set to True, ignore the cache and run the computations
        for the solver anyway. Else, use the cache if available.
    collect : bool
        If set to True, only collect the results that have been put in cache,
        and ignore the results that are not computed yet, default is False.
    terminal : TerminalOutput or None
        Object to format string to display the progress of the solver.
    run_context : RunContext | None
        Base context created in ``_run_benchmark`` carrying config fields
        (``pdb``, ``run_output_base``).  Cloned here for each repetition
        with the per-run fields filled in.

    Returns
    -------
    args_run_one_to_cvg : dict
        The dictionary of arguments to run_one_to_cvg.
    """
    run_context = run_context or RunContext()

    # Resolve inheritance now rather than at `_set_objective` run time: meta
    # below feeds the cache key, so it must not depend on whether some other
    # (solver, dataset) pair already triggered this resolution earlier on.
    solver._inherit_stopping_criterion(objective)

    # get sampling strategy
    # for plotting purpose consider 'callback' as 'iteration'
    sampling_strategy = solver._solver_strategy
    if sampling_strategy == 'callback':
        sampling_strategy = 'iteration'

    # get objective description
    # use `obj_` instead of `objective_` to avoid conflicts with
    # the name of metrics in Objective.compute
    obj_description = objective.__doc__ or ""

    # Set run context with rep=0 so get_seed() works during _set_dataset.
    run_context = run_context.set_run_context(
        objective=objective, dataset=dataset, solver=solver,
        repetition=0, base_seed=benchmark.seed,
    )

    # Set objective and skip if necessary.
    skip, reason = objective._set_dataset(dataset)
    if skip:
        terminal.skip(reason, objective=True)
        return []

    if n_repetitions is None:
        if hasattr(objective, "cv"):
            n_repetitions = objective.cv.get_n_splits(
                **getattr(objective, "cv_metadata", {})
            )
        else:
            # we set 1 by default so that the solver run at least once
            n_repetitions = 1

    terminal.n_repetitions = n_repetitions

    for rep in range(n_repetitions):
        objective_rep = copy.copy(objective)
        objective_rep._repetition = rep

        # Get meta
        meta = {
            'base_seed': benchmark.seed,
            'objective_name': str(objective),
            'obj_description': obj_description,
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

        # Set dataset in objective for the repetition.
        # We need to set the context here, used in get_data. No need to clone
        # each components, they are cloned and reset for each run .
        run_ctx = run_context.set_run_context(
            objective=objective_rep, dataset=dataset, solver=solver,
            repetition=rep, base_seed=benchmark.seed,
        )
        objective_rep._set_dataset(dataset)

        args_run_one_to_cvg = dict(
            benchmark=benchmark, objective=objective_rep, solver=solver,
            meta=meta, timeout=timeout, max_runs=max_runs, force=force,
            terminal=terminal, run_context=run_ctx,
        )

        yield args_run_one_to_cvg


def generate_run_kwargs(
    benchmark, solvers=None, forced_solvers=None, datasets=None,
    objectives=None, n_repetitions=1, max_runs=10, timeout=None,
    collect=False, terminal=None, run_context=None,
):
    """Yield kwargs for each ``run_one_to_cvg`` call in the benchmark.

    Combines the (dataset, objective, solver) enumeration with the per-run
    metadata so that callers only need a single generator to drive the
    benchmark execution.
    """
    all_runs = _get_all_runs(
        benchmark, solvers, forced_solvers, datasets, objectives,
        terminal=terminal,
    )
    common_kwargs = dict(
        benchmark=benchmark, n_repetitions=n_repetitions, max_runs=max_runs,
        timeout=timeout, collect=collect, run_context=run_context,
    )
    for kwargs in all_runs:
        yield from get_solver_kwargs(**common_kwargs, **kwargs)
