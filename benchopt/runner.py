import time

from datetime import datetime

from joblib import Parallel, delayed

from .callback import _Callback
from .benchmark import _check_name_lists
from .utils.sys_info import get_sys_info
from .utils.pdb_helpers import exception_handler

from .utils.terminal_output import TerminalOutput

# For compat with the lasso benchmark, expose INFINITY in this module.
# Should be removed once benchopt/benchmark_lasso#55 is merged
from .stopping_criterion import INFINITY  # noqa: F401


##################################
# Time one run of a solver
##################################
def run_one_resolution(objective, solver, meta, stop_val):
    """Run one resolution of the solver.

    Parameters
    ----------
    objective : instance of BaseObjective
        The objective to minimize.
    solver : instance of BaseSolver
        The solver to use.
    meta : dict
        Metadata passed to store in Cost results.
        Contains objective, data, dimension, id_rep.
    stop_val : int | float
        Corresponds to stopping criterion, such as
        tol or max_iter for the solver. It depends
        on the stopping_strategy for the solver.

    Returns
    -------
    cost : dict
        Details on the run and the objective value obtained.
    """
    # check if the module caught a failed import
    if not solver.is_installed():
        raise ImportError(
            f"Failure during import in {solver.__module__}."
        )

    t_start = time.perf_counter()
    solver.run(stop_val)
    delta_t = time.perf_counter() - t_start
    beta_hat_i = solver.get_result()
    objective_dict = objective(beta_hat_i)

    # Add system info in results
    info = get_sys_info()

    return dict(**meta, stop_val=stop_val, time=delta_t,
                **objective_dict, **info)


def run_one_to_cvg(benchmark, objective, solver, meta, stopping_criterion,
                   force=False, output=None, pdb=False):
    """Run all repetitions of the solver for a value of stopping criterion.

    Parameters
    ----------
    benchmark : benchopt.Benchmark object
        Object to represent the benchmark.
    objective : instance of BaseObjective
        The objective to minimize.
    solver : instance of BaseSolver
        The solver to use.
    meta : dict
        Metadata passed to store in Cost results.
        Contains objective, data, dimension.
    stopping_criterion : StoppingCriterion
        Object to check if we need to stop a solver.
    force : bool
        If force is set to True, ignore the cache and run the computations
        for the solver anyway. Else, use the cache if available.
    pdb : bool
        It pdb is set to True, open a debugger on error.

    Returns
    -------
    curve : list of Cost
        The cost obtained for all repetitions.
    status : 'done' | 'diverged' | 'timeout' | 'max_runs'
        The status on which the solver was stopped.
    """

    curve = []
    with exception_handler(output, pdb=pdb) as ctx:

        if solver._solver_strategy == "callback":
            output.progress('empty run for compilation')
            run_once_cb = _Callback(
                lambda x: {'objective_value': 1},
                {},
                stopping_criterion.get_runner_instance(
                    solver=solver, max_runs=1
                )
            )
            solver.run(run_once_cb)

            # If stopping strategy is 'callback', only call once to get the
            # results up to convergence.
            callback = _Callback(
                objective, meta, stopping_criterion
            )
            solver.run(callback)
            curve, ctx.status = callback.get_results()
        else:

            # Create a Memory object to cache the computations in the benchmark
            # folder and handle cases where we force the run.
            run_one_resolution_cached = benchmark.cache(
                run_one_resolution, force
            )

            # compute initial value
            call_args = dict(objective=objective, solver=solver, meta=meta)

            stop = False
            stop_val = stopping_criterion.init_stop_val()
            while not stop:

                cost = run_one_resolution_cached(stop_val=stop_val,
                                                 **call_args)
                curve.append(cost)

                # Check the stopping criterion and update rho if necessary.
                stop, ctx.status, stop_val = stopping_criterion.should_stop(
                    stop_val, curve
                )

    return curve, ctx.status


def run_one_solver(benchmark, dataset, objective, solver, n_repetitions,
                   max_runs, timeout, force=False, output=None, pdb=False):
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
    output : TerminalOutput or None
        Object to format string to display the progress of the solver.
    pdb : bool
        It pdb is set to True, open a debugger on error.

    Returns
    -------
    run_statistics : list
        The benchmark results.
    """
    run_one_to_cvg_cached = benchmark.cache(
        run_one_to_cvg, ignore=['force', 'output', 'pdb']
    )

    # Set objective an skip if necessary.
    skip, reason = objective.set_dataset(dataset)
    if skip:
        output.skip(reason, objective=True)
        return []

    objective.set_dataset(dataset)
    skip, reason = solver._set_objective(objective)
    if skip:
        output.skip(reason)
        return []

    states = []
    run_statistics = []
    for rep in range(n_repetitions):

        output.set(rep=rep)
        # Get meta
        meta = dict(
            objective_name=str(objective),
            solver_name=str(solver),
            data_name=str(dataset),
            idx_rep=rep,
        )

        stopping_criterion = solver.stopping_criterion.get_runner_instance(
            solver=solver,
            max_runs=max_runs,
            timeout=timeout / n_repetitions,
            output=output,
        )
        curve, status = run_one_to_cvg_cached(
            benchmark=benchmark, objective=objective,
            solver=solver, meta=meta,
            stopping_criterion=stopping_criterion,
            force=force, output=output, pdb=pdb
        )
        if status in ['diverged', 'error', 'interrupted']:
            break
        run_statistics.extend(curve)
        states.append(status)

    else:
        if 'max_runs' in states:
            status = 'max_runs'
        elif 'timeout' in states:
            status = 'timeout'
        else:
            status = 'done'

    output.show_status(status=status)
    # Make sure to flush so the parallel output is properly display
    print(flush=True)

    if status == 'interrupted':
        raise SystemExit(1)
    return run_statistics


def run_benchmark(benchmark, solver_names=None, forced_solvers=None,
                  dataset_names=None, objective_filters=None,
                  max_runs=10, n_repetitions=1, timeout=100, n_jobs=1,
                  plot_result=True, html=True, show_progress=True, pdb=False):
    """Run full benchmark.

    Parameters
    ----------
    benchmark : benchopt.Benchmark object
        Object to represent the benchmark.
    solver_names : list | None
        List of solvers to include in the benchmark. If None
        all solvers available are run.
    forced_solvers : list | None
        List of solvers to include in the benchmark and for
        which one forces recomputation.
    dataset_names : list | None
        List of datasets to include. If None all available
        datasets are used.
    objective_filters : list | None
        Filters to select specific objective parameters. If None,
        all objective parameters are tested
    max_runs : int
        The maximum number of solver runs to perform to estimate
        the convergence curve.
    n_repetitions : int
        The number of repetitions to run. Defaults to 1.
    timeout : float
        The maximum duration in seconds of the solver run.
    n_jobs : int
        Maximal number of workers to use to run the benchmark in parallel.
    plot_result : bool
        If set to True (default), display the result plot and save them in
        the benchmark directory.
    html : bool
        If set to True (default), display the result plot in HTML, otherwise
        in matplotlib figures, default is True.
    show_progress : bool
        If show_progress is set to True, display the progress of the benchmark.
    pdb : bool
        It pdb is set to True, open a debugger on error.

    Returns
    -------
    df : instance of pandas.DataFrame
        The benchmark results. If multiple metrics were computed, each
        one is stored in a separate column. If the number of metrics computed
        by the objective is not the same for all parameters, the missing data
        is set to `NaN`.
    """
    print("Benchopt is running")

    # List all datasets, objective and solvers to run based on the filters
    # provided. Merge the solver_names and forced to run all necessary solvers.
    solver_names = _check_name_lists(solver_names, forced_solvers)
    output = TerminalOutput(n_repetitions, show_progress)

    output.set(verbose=True)
    all_runs = benchmark.get_all_runs(
        solver_names, forced_solvers, dataset_names, objective_filters,
        output=output
    )

    results = Parallel(n_jobs=n_jobs)(
        delayed(run_one_solver)(
            benchmark=benchmark, dataset=dataset, objective=objective,
            solver=solver, n_repetitions=n_repetitions, max_runs=max_runs,
            timeout=timeout, force=force, output=output, pdb=pdb
        ) for dataset, objective, solver, force, output in all_runs
    )

    run_statistics = []
    for curve in results:
        run_statistics.extend(curve)

    import pandas as pd
    df = pd.DataFrame(run_statistics)
    if df.empty:
        output.savefile_status()
        raise SystemExit(1)

    # Save output in CSV file in the benchmark folder
    timestamp = datetime.now().strftime('%Y-%m-%d_%Hh%Mm%S')
    output_dir = benchmark.get_output_folder()
    save_file = output_dir / f'benchopt_run_{timestamp}.csv'
    df.to_csv(save_file)
    output.savefile_status(save_file=save_file)

    if plot_result:
        from benchopt.plotting import plot_benchmark
        plot_benchmark(save_file, benchmark, html=html)
    return save_file
